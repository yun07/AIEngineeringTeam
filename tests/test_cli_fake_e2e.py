"""Fake-mode CLI end to end, with a test-only approver.

The production default stays deny-by-default: the non-interactive test proves
it. Only the success tests replace the gate with an explicit stub, and they
never change the shipped behaviour.
"""

from __future__ import annotations

import builtins
import hashlib
import sys

from aiteam import cli
from tests.fakes import approving_gate

REQUEST = "Create a demo notes file"


def _run_cli(root, extra=()):
    return cli.main(
        [
            "run",
            "--fake",
            "--project",
            "demo",
            "--request",
            REQUEST,
            "--budget",
            "0.50",
            "--root",
            str(root),
            *extra,
        ]
    )


def test_fake_cli_run_completes_with_an_injected_approver(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "build_approval_gate", approving_gate)

    exit_code = _run_cli(tmp_path)

    assert exit_code == 0

    run_dirs = list((tmp_path / "runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    report = (run_dir / "report.md").read_text(encoding="utf-8")

    assert "| Run state | `completed` |" in report
    assert "## QA evidence" in report
    assert "Engine result: accepted" in report
    assert "python -m pytest qa_tests -q" in report
    assert "Fake mode: no billable usage or USD cost." in report

    project = tmp_path / "projects" / "demo"
    assert (project / "notes.md").is_file()
    assert (project / "qa_tests" / "test_notes.py").is_file()
    assert not (tmp_path / "state" / "usage.jsonl").exists()

    approvals = (tmp_path / "state" / "approvals.jsonl").read_text(encoding="utf-8")
    assert '"decision": "approved"' in approvals


def test_fake_cli_accepts_a_context_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "build_approval_gate", approving_gate)
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    brief = context_dir / "brief.md"
    brief.write_text("## Alpha\nAlpha detail.\n", encoding="utf-8")

    exit_code = cli.main(
        [
            "run",
            "--fake",
            "--project",
            "demo",
            "--request",
            REQUEST,
            "--budget",
            "0.50",
            "--root",
            str(tmp_path),
            "--context-file",
            "context/brief.md",
        ]
    )

    assert exit_code == 0
    run_dir = next((tmp_path / "runs").iterdir())
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    sha256 = hashlib.sha256(brief.read_bytes()).hexdigest()
    assert "## Context" in report
    assert "brief.md" in report
    assert sha256 in report
    assert (run_dir / "context" / "manifest.json").is_file()
    assert (run_dir / "context" / "01-brief.md").is_file()


def test_fake_cli_run_without_tty_is_blocked_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    def refuse_input():
        raise AssertionError("input() must not be called without a TTY")

    monkeypatch.setattr(builtins, "input", refuse_input)

    exit_code = _run_cli(tmp_path)

    assert exit_code == 1

    run_dir = next((tmp_path / "runs").iterdir())
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "approval_denied" in report
    assert "No commands executed." in report
