"""Missing criterion scenario: engine rejects incomplete coverage."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from tests.fakes import event_kinds, qa_script, run_demo

TWO_CRITERIA_PLAN = {
    "tasks": [
        {
            "id": "T1",
            "description": "Create the notes file and keep it stable.",
            "acceptance_criteria": [
                {"id": "C1", "text": "notes.md exists."},
                {"id": "C2", "text": "notes.md is stable across reads."},
            ],
            "constraints": ["Plain text only."],
        }
    ]
}


def test_missing_criterion_blocks_with_a_named_reason(tmp_path):
    only_c1 = qa_script(
        checks=(
            {
                "criterion": "C1",
                "name": "notes exist",
                "kind": "positive",
                "exit_code": 0,
                "test_file": "qa_tests/test_demo.py",
            },
            {
                "criterion": "C1",
                "name": "missing file stays absent",
                "kind": "negative",
                "exit_code": 0,
                "test_file": "qa_tests/test_demo.py",
            },
        )
    )

    # One allowed attempt: the first engine-confirmed QA failure escalates.
    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=only_c1,
        plan=TWO_CRITERIA_PLAN,
        max_attempts=1,
    )

    assert result.state is RunState.ESCALATED
    reason = result.block_reason or ""
    assert "attempts_exhausted" in reason
    assert "missing_criterion: C2" in reason
    assert result.tasks[0].state is TaskState.ESCALATED
    assert result.tasks[0].attempt == 1
    assert "missing_criterion: C2" in (result.tasks[0].qa_failure_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_qa_failed" in kinds
    assert "task_escalated" in kinds
    assert "run_escalated" in kinds

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Engine result: **rejected**" in report
    assert "missing_criterion: C2" in report
