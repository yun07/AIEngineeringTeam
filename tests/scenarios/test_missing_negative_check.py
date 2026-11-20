"""Missing negative check scenario: engine rejects a verdict without one."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from tests.fakes import qa_script, run_demo


def test_verdict_without_a_negative_check_is_rejected(tmp_path):
    positive_only = qa_script(
        checks=(
            {
                "criterion": "C1",
                "name": "notes exist",
                "kind": "positive",
                "exit_code": 0,
                "test_file": "qa_tests/test_demo.py",
            },
        )
    )

    _, store, run, result = run_demo(
        tmp_path, qa_script_responses=positive_only
    )

    assert result.state is RunState.BLOCKED
    reason = result.block_reason or ""
    assert "qa_failed_no_retry_in_m2" in reason
    assert "missing_negative_check" in reason
    assert result.tasks[0].state is TaskState.QA_FAILED

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "missing_negative_check" in report
