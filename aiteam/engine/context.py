"""Engine-owned context files and section scoping.

The engine, never an agent, reads context files. Content is bounded, hashed
and copied into the run directory so the prompt and the manifest agree.
Mandatory context is not handled here; it is assembled from role prompts.
"""

from __future__ import annotations

import hashlib
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

MAX_CONTEXT_FILES = 5
MAX_TOTAL_CONTEXT_BYTES = 64 * 1024

_HEADING = re.compile(r"(?m)^##\s+(.+?)\s*$")


class ContextError(ValueError):
    """Raised when a context file is missing, unsafe or too large."""


@dataclass(frozen=True)
class ContextSection:
    id: str
    heading: str
    text: str
    source_name: str
    source_sha256: str


@dataclass
class ContextDocument:
    name: str
    sha256: str
    size_bytes: int
    text: str
    sections: list[ContextSection] = field(default_factory=list)


@dataclass
class ContextBundle:
    documents: list[ContextDocument] = field(default_factory=list)

    @property
    def sections(self) -> list[ContextSection]:
        return [section for document in self.documents for section in document.sections]

    @property
    def section_ids(self) -> set[str]:
        return {section.id for section in self.sections}

    def manifest(self) -> dict[str, object]:
        return {
            "total_bytes": sum(document.size_bytes for document in self.documents),
            "files": [
                {
                    "name": document.name,
                    "sha256": document.sha256,
                    "bytes": document.size_bytes,
                    "sections": [
                        {"id": section.id, "heading": section.heading}
                        for section in document.sections
                    ],
                }
                for document in self.documents
            ],
        }

    def summary(self) -> list[dict[str, object]]:
        return [
            {
                "name": document.name,
                "sha256": document.sha256,
                "bytes": document.size_bytes,
            }
            for document in self.documents
        ]

    def copies(self) -> list[tuple[str, str]]:
        return [
            (f"{index:02d}-{document.name}", document.text)
            for index, document in enumerate(self.documents, start=1)
        ]

    def inventory(self) -> str:
        lines = []
        for document in self.documents:
            for section in document.sections:
                lines.append(
                    f"- {section.id}: {section.heading} "
                    f"(source {document.name}, sha256 {document.sha256[:12]})"
                )
        return "\n".join(lines) if lines else "(no context sections)"

    def render_for_orchestrator(self) -> str:
        if not self.documents:
            return ""
        blocks: list[str] = []
        for index, document in enumerate(self.documents, start=1):
            body = "\n\n".join(
                f"[{section.id}] ## {section.heading}\n{section.text}"
                for section in document.sections
            )
            blocks.append(
                f"=== BEGIN CONTEXT SOURCE {index}: {document.name} "
                f"(sha256={document.sha256}, {document.size_bytes} bytes) ===\n"
                f"{body}\n"
                f"=== END CONTEXT SOURCE {index} ==="
            )
        return "\n\n".join(blocks)

    def render_sections(self, ids: Iterable[str]) -> str:
        wanted = list(dict.fromkeys(ids))
        if not wanted:
            return ""
        by_id = {section.id: section for section in self.sections}
        missing = [section_id for section_id in wanted if section_id not in by_id]
        if missing:
            raise ContextError(f"unknown context section ids: {missing}")

        blocks: list[str] = []
        for index, document in enumerate(self.documents, start=1):
            selected = [
                section
                for section in document.sections
                if section.id in wanted
            ]
            if not selected:
                continue
            body = "\n\n".join(
                f"[{section.id}] ## {section.heading}\n{section.text}"
                for section in selected
            )
            blocks.append(
                f"=== BEGIN CONTEXT SOURCE {index}: {document.name} "
                f"(sha256={document.sha256}, {document.size_bytes} bytes) ===\n"
                f"{body}\n"
                f"=== END CONTEXT SOURCE {index} ==="
            )
        return "\n\n".join(blocks)


def _normalized_name(name: str) -> str:
    return name.rstrip(" .").casefold()


def _is_secret_name(path: Path) -> bool:
    return any(
        _normalized_name(part).startswith(".env") for part in path.parts
    )


def _split_sections(
    text: str, *, name: str, sha256: str, start_index: int
) -> list[ContextSection]:
    matches = list(_HEADING.finditer(text))
    sections: list[ContextSection] = []
    index = start_index

    if not matches:
        return [
            ContextSection(
                id=f"S{index}",
                heading=Path(name).stem,
                text=text.strip(),
                source_name=name,
                source_sha256=sha256,
            )
        ]

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(
            ContextSection(
                id=f"S{index}",
                heading="(preamble)",
                text=preamble,
                source_name=name,
                source_sha256=sha256,
            )
        )
        index += 1

    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        sections.append(
            ContextSection(
                id=f"S{index}",
                heading=match.group(1).strip(),
                text=body,
                source_name=name,
                source_sha256=sha256,
            )
        )
        index += 1
    return sections


def load_context_files(
    paths: Sequence[str],
    *,
    root: str | Path,
    max_files: int = MAX_CONTEXT_FILES,
    max_total_bytes: int = MAX_TOTAL_CONTEXT_BYTES,
) -> ContextBundle:
    if not paths:
        return ContextBundle()
    if len(paths) > max_files:
        raise ContextError(
            f"at most {max_files} context files are allowed, got {len(paths)}"
        )

    root_path = Path(root).resolve()
    documents: list[ContextDocument] = []
    total_bytes = 0
    next_section = 1

    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            raise ContextError("context file paths must be non-empty strings")
        given = Path(raw)
        candidate = given if given.is_absolute() else root_path / given

        if _is_secret_name(candidate):
            raise ContextError(f"secret-like context file is refused: {raw}")
        if candidate.is_symlink():
            raise ContextError(f"symlinked context files are refused: {raw}")

        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ContextError(f"context file does not exist: {raw}") from exc

        if resolved != root_path and root_path not in resolved.parents:
            raise ContextError(
                f"context file resolves outside the repository: {raw}"
            )
        if not stat.S_ISREG(resolved.stat().st_mode):
            raise ContextError(f"context path is not a regular file: {raw}")
        if _is_secret_name(resolved):
            raise ContextError(f"secret-like context file is refused: {raw}")

        data = resolved.read_bytes()
        total_bytes += len(data)
        if total_bytes > max_total_bytes:
            raise ContextError(
                f"context files exceed {max_total_bytes} bytes in total"
            )
        if b"\x00" in data:
            raise ContextError(f"context file contains NUL bytes: {raw}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContextError(f"context file is not valid UTF-8: {raw}") from exc

        sha256 = hashlib.sha256(data).hexdigest()
        name = resolved.name
        sections = _split_sections(
            text, name=name, sha256=sha256, start_index=next_section
        )
        next_section += len(sections)
        documents.append(
            ContextDocument(
                name=name,
                sha256=sha256,
                size_bytes=len(data),
                text=text,
                sections=sections,
            )
        )

    return ContextBundle(documents=documents)


def require_sections(bundle: ContextBundle | None, ids: Sequence[str]) -> None:
    if not ids:
        return
    if bundle is None:
        raise ContextError("context_refs were used but no context files were supplied")
    missing = sorted(set(ids) - bundle.section_ids)
    if missing:
        raise ContextError(f"context_refs point to unknown sections: {missing}")


def context_files_summary(paths: Sequence[str]) -> Mapping[str, object]:
    return {"requested_files": len(paths)}
