"""Context manifest, hashes and reproducible copies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aiteam.engine.context import load_context_files
from aiteam.state.store import StateStore


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def test_artifacts_are_written_with_hashes_and_no_absolute_paths(tmp_path):
    root = _root(tmp_path)
    source = root / "brief.md"
    source.write_text("## Alpha\nA text.\n", encoding="utf-8")
    bundle = load_context_files(["brief.md"], root=root)
    store = StateStore(root)

    context_dir = store.write_context_artifacts(
        "run-1", bundle.manifest(), bundle.copies()
    )

    manifest_path = context_dir / "manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    assert manifest["files"][0]["name"] == "brief.md"
    assert manifest["files"][0]["sha256"] == hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    assert manifest["files"][0]["bytes"] == source.stat().st_size
    assert str(root) not in manifest_text
    assert str(tmp_path) not in manifest_text

    copy = context_dir / "01-brief.md"
    assert copy.is_file()
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == manifest["files"][0]["sha256"]


def test_bundle_summary_is_safe_for_run_state(tmp_path):
    root = _root(tmp_path)
    (root / "brief.md").write_text("## Alpha\nA text.\n", encoding="utf-8")
    bundle = load_context_files(["brief.md"], root=root)

    summary = bundle.summary()

    assert summary == [
        {
            "name": "brief.md",
            "sha256": bundle.documents[0].sha256,
            "bytes": bundle.documents[0].size_bytes,
        }
    ]
    assert str(root) not in json.dumps(summary)


def test_sections_in_manifest_match_loaded_sections(tmp_path):
    root = _root(tmp_path)
    (root / "brief.md").write_text(
        "## Alpha\nA text.\n\n## Beta\nB text.\n", encoding="utf-8"
    )
    bundle = load_context_files(["brief.md"], root=root)

    manifest = bundle.manifest()

    assert [entry["id"] for entry in manifest["files"][0]["sections"]] == ["S1", "S2"]
    assert [section.heading for section in bundle.sections] == ["Alpha", "Beta"]
