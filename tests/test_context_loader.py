"""Context file loading: limits, encoding, secrets, traversal and symlinks."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from aiteam.engine.context import (
    MAX_TOTAL_CONTEXT_BYTES,
    ContextError,
    load_context_files,
)


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def test_loads_sections_and_hashes_content(tmp_path):
    root = _root(tmp_path)
    path = root / "brief.md"
    content = "# Brief\n\nIntro text.\n\n## Alpha\nA text.\n\n## Beta\nB text.\n"
    path.write_text(content, encoding="utf-8")

    bundle = load_context_files(["brief.md"], root=root)

    assert len(bundle.documents) == 1
    document = bundle.documents[0]
    assert document.name == "brief.md"
    assert document.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert document.size_bytes == len(path.read_bytes())
    assert [section.id for section in bundle.sections] == ["S1", "S2", "S3"]
    assert bundle.sections[0].heading == "(preamble)"
    assert bundle.sections[1].heading == "Alpha"
    assert set(bundle.section_ids) == {"S1", "S2", "S3"}


def test_rejects_more_than_five_files(tmp_path):
    root = _root(tmp_path)
    paths = []
    for index in range(6):
        path = root / f"c{index}.md"
        path.write_text(f"## S\n{index}\n", encoding="utf-8")
        paths.append(path.name)

    with pytest.raises(ContextError, match="at most 5"):
        load_context_files(paths, root=root)


def test_rejects_total_size_over_the_limit(tmp_path):
    root = _root(tmp_path)
    half = b"a" * (MAX_TOTAL_CONTEXT_BYTES // 2 + 1)
    (root / "one.md").write_bytes(half)
    (root / "two.md").write_bytes(half)

    with pytest.raises(ContextError, match="exceed"):
        load_context_files(["one.md", "two.md"], root=root)


def test_rejects_nul_bytes(tmp_path):
    root = _root(tmp_path)
    (root / "nul.md").write_bytes(b"## A\ntext\x00more\n")

    with pytest.raises(ContextError, match="NUL"):
        load_context_files(["nul.md"], root=root)


def test_rejects_invalid_utf8(tmp_path):
    root = _root(tmp_path)
    (root / "bad.md").write_bytes(b"## A\n\xff\xfe\n")

    with pytest.raises(ContextError, match="UTF-8"):
        load_context_files(["bad.md"], root=root)


def test_rejects_secret_like_names(tmp_path):
    root = _root(tmp_path)
    (root / ".env").write_text("OPENAI_API_KEY=x\n", encoding="utf-8")

    with pytest.raises(ContextError, match="secret-like"):
        load_context_files([".env"], root=root)


def test_rejects_non_regular_files(tmp_path):
    root = _root(tmp_path)
    (root / "folder").mkdir()

    with pytest.raises(ContextError, match="not a regular file"):
        load_context_files(["folder"], root=root)


def test_rejects_paths_outside_the_repository(tmp_path):
    root = _root(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("## A\noutside\n", encoding="utf-8")

    with pytest.raises(ContextError, match="outside the repository"):
        load_context_files(["../outside.md"], root=root)


def test_rejects_missing_files(tmp_path):
    root = _root(tmp_path)

    with pytest.raises(ContextError, match="does not exist"):
        load_context_files(["missing.md"], root=root)


def test_rejects_symlinked_context_file(tmp_path):
    root = _root(tmp_path)
    target = root / "real.md"
    target.write_text("## A\nreal\n", encoding="utf-8")
    link = root / "link.md"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")

    with pytest.raises(ContextError, match="symlinked"):
        load_context_files(["link.md"], root=root)


def test_empty_paths_returns_empty_bundle(tmp_path):
    bundle = load_context_files([], root=_root(tmp_path))

    assert bundle.documents == []
    assert bundle.sections == []
    assert bundle.render_for_orchestrator() == ""
