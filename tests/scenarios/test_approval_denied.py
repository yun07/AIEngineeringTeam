"""Approval denied scenario: blocked run, recorded denial, no execution."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from tests.fakes import (
    ScriptedRunner,
    denying_gate,
    event_kinds,
    qa_script,
    run_demo,
)


def test_denied_execution_blocks_without_running(tmp_path):
    runner = ScriptedRunner()
    gate = denying_gate()

    _, store, run, result = run_demo(
        tmp_path, qa_script_responses=qa_script(), gate=gate, runner=runner
    )

    assert result.state is RunState.BLOCKED
    reason = result.block_reason or ""
    assert "approval_denied" in reason
    assert result.tasks[0].state is TaskState.BLOCKED

    assert runner.calls == []
    assert len(gate.requested) == 1

    approvals = store.read_approvals(run.id)
    assert len(approvals) == 1
    assert approvals[0]["decision"] == "denied"
    assert approvals[0]["reason"] == "user_denied"

    project = tmp_path / "repo" / "projects" / "demo"
    assert (project / "qa_tests" / "test_demo.py").is_file()

    kinds = event_kinds(store, run.id)
    assert "command_denied" in kinds
    assert "task_blocked" in kinds
    assert "run_blocked" in kinds
    assert "command_executed" not in kinds

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "## Approvals" in report
    assert "user_denied" in report
    assert "No commands executed." in report
    assert "Engine result: **rejected**" in report
    assert "Engine result: accepted" not in report
