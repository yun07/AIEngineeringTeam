"""Filesystem tool guards: containment, secret denial and role write limits."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aiteam.tools.filesystem import FileTools, PathDenied, Workspace


def _symlink_or_skip(target: Path, link: Path, *, directory: bool) -> None:
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")


def _qa_tools(root: Path) -> FileTools:
    return FileTools(Workspace(root, write_allow_subpaths=("qa_tests",)))


def _tools(root):
    workspace = Workspace(root, write_deny_subpaths=("qa_tests",))
    return FileTools(workspace), workspace


def test_write_read_and_list(tmp_path):
    tools, _ = _tools(tmp_path / "project")

    tools.write_text("notes.md", "hello\n")
    tools.write_text("pkg/module.py", "value = 1\n")

    assert tools.read_text("notes.md") == "hello\n"
    assert "notes.md" in tools.list_dir(".")
    assert "pkg/" in tools.list_dir(".")


def test_parent_traversal_is_denied(tmp_path):
    tools, _ = _tools(tmp_path / "project")

    with pytest.raises(PathDenied):
        tools.write_text("../escape.md", "nope")
    assert not (tmp_path / "escape.md").exists()


def test_absolute_path_is_denied(tmp_path):
    tools, _ = _tools(tmp_path / "project")

    with pytest.raises(PathDenied):
        tools.read_text(str(tmp_path / "project" / "notes.md"))


def test_env_file_is_denied(tmp_path):
    tools, _ = _tools(tmp_path / "project")
    (tmp_path / "project" / ".env").write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")

    with pytest.raises(PathDenied):
        tools.read_text(".env")
    with pytest.raises(PathDenied):
        tools.write_text(".env", "leak")


def test_developer_cannot_write_into_qa_tests(tmp_path):
    tools, _ = _tools(tmp_path / "project")
    qa_dir = tmp_path / "project" / "qa_tests"
    qa_dir.mkdir(parents=True, exist_ok=True)
    (qa_dir / "test_keep.py").write_text(
        "def test_keep():\n    assert True\n", encoding="utf-8"
    )

    assert "test_keep.py" in tools.list_dir("qa_tests")
    with pytest.raises(PathDenied):
        tools.write_text("qa_tests/test_blocked.py", "def test_x():\n    assert True\n")
    assert not (tmp_path / "project" / "qa_tests" / "test_blocked.py").exists()


def test_tool_specs_contain_no_shell(tmp_path):
    tools, _ = _tools(tmp_path / "project")

    names = {spec.name for spec in tools.tool_specs()}

    assert names == {"read_file", "write_file", "list_files"}


def test_qa_allowlist_permits_only_qa_tests(tmp_path):
    qa_tools = FileTools(
        Workspace(tmp_path / "project", write_allow_subpaths=("qa_tests",))
    )

    qa_tools.write_text("qa_tests/test_ok.py", "def test_ok():\n    assert True\n")
    assert (tmp_path / "project" / "qa_tests" / "test_ok.py").is_file()

    for path in (
        "notes.md",
        "src/app.py",
        "pkg/qa_tests/test_x.py",
        "runs/report.md",
        "state/index.json",
    ):
        with pytest.raises(PathDenied):
            qa_tools.write_text(path, "nope")
        assert not (tmp_path / "project" / path).exists()


def test_qa_allowlist_normalises_trailing_dot_and_case(tmp_path):
    qa_tools = FileTools(
        Workspace(tmp_path / "project", write_allow_subpaths=("qa_tests",))
    )

    qa_tools.write_text("QA_TESTS/test_upper.py", "x = 1\n")
    qa_tools.write_text("qa_tests./test_dot.py", "x = 1\n")

    assert (tmp_path / "project" / "qa_tests" / "test_upper.py").is_file()
    with pytest.raises(PathDenied):
        qa_tools.write_text("qa_tests_evil/test_x.py", "nope")


def test_developer_deny_applies_at_any_depth(tmp_path):
    tools, _ = _tools(tmp_path / "project")

    with pytest.raises(PathDenied):
        tools.write_text("pkg/qa_tests/test_x.py", "nope")
    with pytest.raises(PathDenied):
        tools.write_text("QA_TESTS./test_x.py", "nope")


def test_qa_tests_directory_symlink_to_outside_is_denied(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    _symlink_or_skip(external, project / "qa_tests", directory=True)

    tools = _qa_tools(project)

    with pytest.raises(PathDenied):
        tools.write_text("qa_tests/escape.py", "x = 1\n")
    assert not (external / "escape.py").exists()


def test_nested_symlink_inside_qa_tests_is_denied(tmp_path):
    project = tmp_path / "project"
    (project / "qa_tests").mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    _symlink_or_skip(external, project / "qa_tests" / "sub", directory=True)

    tools = _qa_tools(project)

    with pytest.raises(PathDenied):
        tools.write_text("qa_tests/sub/escape.py", "x = 1\n")
    assert not (external / "escape.py").exists()


def test_file_symlink_inside_qa_tests_is_denied(tmp_path):
    project = tmp_path / "project"
    (project / "qa_tests").mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("original\n", encoding="utf-8")
    _symlink_or_skip(outside_file, project / "qa_tests" / "link.py", directory=False)

    tools = _qa_tools(project)

    with pytest.raises(PathDenied):
        tools.write_text("qa_tests/link.py", "overwritten\n")
    assert outside_file.read_text(encoding="utf-8") == "original\n"
