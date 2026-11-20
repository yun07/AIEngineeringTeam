"""Path-contained file operations for every role.

The checks here are guardrails against mistakes, not a security boundary.
They reject absolute paths, ``..`` traversal, anything resolving outside the
workspace, and any path that looks like a secret store such as ``.env``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aiteam.providers.base import ToolSpec

SECRET_NAMES = (".env",)


def normalize_part(part: str) -> str:
    """Normalise one path component for comparison.

    Windows ignores trailing dots and spaces, so ``qa_tests.`` and ``qa_tests``
    name the same directory. Comparison must not rely on the raw spelling.
    """
    return part.rstrip(" .").casefold()


class PathDenied(PermissionError):
    """Raised when a requested path is outside the allowed workspace."""


class Workspace:
    def __init__(
        self,
        root: str | Path,
        *,
        write_deny_subpaths: tuple[str, ...] = (),
        write_allow_subpaths: tuple[str, ...] = (),
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.write_deny_subpaths = tuple(
            normalize_part(item) for item in write_deny_subpaths
        )
        self.write_allow_subpaths = tuple(
            normalize_part(item) for item in write_allow_subpaths
        )

    def resolve(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative.strip():
            raise PathDenied("path must be a non-empty string")
        candidate = Path(relative)
        if candidate.is_absolute():
            raise PathDenied(f"absolute paths are not allowed: {relative}")

        resolved = (self.root / candidate).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise PathDenied(f"path escapes the workspace: {relative}")

        for part in resolved.relative_to(self.root).parts:
            lowered = normalize_part(part)
            if lowered in SECRET_NAMES or lowered.startswith(".env"):
                raise PathDenied(f"access to secret-like path is denied: {relative}")
        return resolved

    def resolve_for_write(self, relative: str) -> Path:
        resolved = self.resolve(relative)
        parts = tuple(
            normalize_part(part) for part in resolved.relative_to(self.root).parts
        )

        if self.write_allow_subpaths:
            if not parts or parts[0] not in self.write_allow_subpaths:
                allowed = ", ".join(sorted(self.write_allow_subpaths))
                raise PathDenied(
                    f"writes are only permitted under {allowed}/: {relative}"
                )

        if parts and self.write_deny_subpaths:
            for part in parts:
                if part in self.write_deny_subpaths:
                    raise PathDenied(
                        f"writes under {part}/ are reserved for another role: {relative}"
                    )
        return resolved


class FileTools:
    """Read, write and list tools shared by roles that hold file permissions."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def tool_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="read_file",
                description="Read a UTF-8 text file inside the project workspace.",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            ToolSpec(
                name="write_file",
                description=(
                    "Write a UTF-8 text file inside the project workspace, "
                    "creating parent directories as needed."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
            ToolSpec(
                name="list_files",
                description="List entries of a directory inside the workspace.",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": [],
                },
            ),
        ]

    def handlers(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {
            "read_file": self._read_handler,
            "write_file": self._write_handler,
            "list_files": self._list_handler,
        }

    def read_text(self, relative: str) -> str:
        path = self.workspace.resolve(relative)
        if not path.is_file():
            raise FileNotFoundError(f"no such file: {relative}")
        return path.read_text(encoding="utf-8")

    def write_text(self, relative: str, content: str) -> Path:
        path = self.workspace.resolve_for_write(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def list_dir(self, relative: str = ".") -> list[str]:
        path = self.workspace.resolve(relative)
        if not path.is_dir():
            raise NotADirectoryError(f"no such directory: {relative}")
        entries = []
        for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            entries.append(f"{item.name}/" if item.is_dir() else item.name)
        return entries

    def _read_handler(self, arguments: dict[str, Any]) -> str:
        return self.read_text(str(arguments.get("path", "")))

    def _write_handler(self, arguments: dict[str, Any]) -> str:
        relative = str(arguments.get("path", ""))
        content = arguments.get("content", "")
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        path = self.write_text(relative, content)
        return f"wrote {len(content)} characters to {path.relative_to(self.workspace.root).as_posix()}"

    def _list_handler(self, arguments: dict[str, Any]) -> str:
        relative = str(arguments.get("path") or ".")
        entries = self.list_dir(relative)
        return "\n".join(entries) if entries else "(empty directory)"
