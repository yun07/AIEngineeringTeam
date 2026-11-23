"""Regression tests for scripts/preflight.py using isolated temporary repositories."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "preflight.py"

PROTOCOL = """# Protocol

## Part 1 — Project Configuration

| Field | Value |
|---|---|
| Project name | Temp project |

## Part 2 — Universal Protocol

Read `AGENTS.md` first.
Read AGENTS.md first, then follow its Mandatory Session Bootstrap.
"""

DEFAULT_DOCS = {
    "AGENTS.md": "# AGENTS\n\n## Mandatory Session Bootstrap\n",
    "README.md": "# README\n",
    "AI_Engineering_Team.md": "# Charter\n",
    "UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md": PROTOCOL,
    "plans/phase1-architecture-plan.md": "# Plan\n",
}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(
    tmp_path: Path, *, branch: str = "review", docs: dict[str, str] | None = None
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Preflight Test")
    for relative, text in (docs or DEFAULT_DOCS).items():
        _write(repo, relative, text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    if branch != "main":
        _git(repo, "checkout", "-q", "-b", branch)
        _write(repo, "README.md", "# README\n\nreview change\n")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-q", "-m", "review change")
    return repo


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def test_review_branch_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "README.md" in result.stdout


def test_main_branch_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, branch="main")
    result = _run(repo)
    assert result.returncode == 1
    assert "current branch is main" in result.stdout


def test_modified_staged_and_untracked_files_are_reported(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write(repo, "README.md", "# README\n\nmodified working tree\n")
    _write(repo, "staged.txt", "staged\n")
    _git(repo, "add", "staged.txt")
    _write(repo, "untracked.txt", "untracked\n")

    result = _run(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    for name in ("README.md", "staged.txt", "untracked.txt"):
        assert name in result.stdout


@pytest.mark.parametrize("marker", ["MERGE_HEAD", "rebase-merge"])
def test_merge_or_rebase_state_fails(tmp_path: Path, marker: str) -> None:
    repo = _make_repo(tmp_path)
    git_dir = repo / ".git"
    if marker == "MERGE_HEAD":
        _write(git_dir, marker, _git(repo, "rev-parse", "HEAD").stdout.strip() + "\n")
    else:
        (git_dir / marker).mkdir()

    result = _run(repo)
    assert result.returncode == 1
    assert "merge in progress" in result.stdout or "rebase in progress" in result.stdout


def test_missing_origin_main_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    result = _run(repo)
    assert result.returncode == 1
    assert "origin/main not found" in result.stdout


def test_unstaged_whitespace_error_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write(repo, "README.md", "# README\n\ntrailing spaces   \n")
    result = _run(repo)
    assert result.returncode == 1
    assert "git diff --check failed" in result.stdout


def test_staged_whitespace_error_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write(repo, "README.md", "# README\n\nstaged trailing spaces   \n")
    _git(repo, "add", "README.md")
    result = _run(repo)
    assert result.returncode == 1
    assert "git diff --cached --check failed" in result.stdout


def test_stale_status_header_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write(
        repo,
        "README.md",
        "# README\n\n**Status:** Canonical, no implementation has started.\n",
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "README.md: stale Status header" in result.stdout


def test_missing_bootstrap_entry_fails(tmp_path: Path) -> None:
    docs = dict(DEFAULT_DOCS)
    docs["UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md"] = PROTOCOL.replace(
        "Read `AGENTS.md` first.\n", ""
    ).replace(
        "Read AGENTS.md first, then follow its Mandatory Session Bootstrap.\n", ""
    )
    repo = _make_repo(tmp_path, docs=docs)
    result = _run(repo)
    assert result.returncode == 1
    assert "bootstrap does not start with AGENTS.md" in result.stdout
    assert "starter command does not start with AGENTS.md" in result.stdout


def test_missing_agents_bootstrap_section_fails(tmp_path: Path) -> None:
    docs = dict(DEFAULT_DOCS)
    docs["AGENTS.md"] = "# AGENTS\n"
    repo = _make_repo(tmp_path, docs=docs)
    result = _run(repo)
    assert result.returncode == 1
    assert "missing the Mandatory Session Bootstrap" in result.stdout


def test_unfilled_part1_placeholder_fails(tmp_path: Path) -> None:
    docs = dict(DEFAULT_DOCS)
    docs["UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md"] = PROTOCOL.replace(
        "| Project name | Temp project |",
        "| Project name | `<PROJECT_NAME>` |",
    )
    repo = _make_repo(tmp_path, docs=docs)
    result = _run(repo)
    assert result.returncode == 1
    assert "unfilled placeholder" in result.stdout


def test_historical_quote_is_not_a_false_positive(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write(
        repo,
        "plans/phase1-architecture-plan.md",
        '# Plan\n\nRevision note: the old "No implementation started" header was removed.\n',
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_non_repository_is_a_failure_not_a_pass(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = _run(empty)
    assert result.returncode == 1
    assert "cannot read repository" in result.stdout
