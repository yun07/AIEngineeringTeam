"""Filesystem tool guards: containment, secret denial and role write limits."""

from __future__ import annotations

import pytest

from aiteam.tools.filesystem import FileTools, PathDenied, Workspace


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
