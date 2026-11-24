"""Retry exhausted scenario: the attempt cap escalates instead of looping."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from aiteam.providers.fake import text_response, tool_response
from aiteam.tools.shell import RunResult
from tests.fakes import (
    ScriptedRunner,
    event_kinds,
    qa_script,
    run_demo,
    write_call,
)

TWO_ATTEMPT_DEVELOPER = [
    tool_response([write_call("notes.md", "first attempt\n")]),
    text_response("Wrote notes.md."),
    tool_response(
        [write_call("notes.md", "second attempt\n", call_id="call_retry_1")]
    ),
    text_response("Rewrote notes.md after the QA feedback."),
]


# Both attempts report a genuine non-zero execution, so both are verifiable.
FAILED_RUN = RunResult(exit_code=1, stdout="1 failed in 0.01s", stderr="")


def test_second_qa_failure_escalates_with_evidence_preserved(tmp_path):
    engine, store, run, result = run_demo(
        tmp_path,
        developer_script=TWO_ATTEMPT_DEVELOPER,
        qa_script_responses=(
            qa_script(verdict="fail", exit_code=1)
            + qa_script(verdict="fail", exit_code=1)
        ),
        runner=ScriptedRunner([FAILED_RUN, FAILED_RUN]),
    )

    assert result.state is RunState.ESCALATED
    task = result.tasks[0]
    assert task.state is TaskState.ESCALATED
    assert task.attempt == 2

    reason = result.block_reason or ""
    assert "attempts_exhausted" in reason
    assert "max_attempts=2" in reason
    assert "qa_reported_fail" in reason

    # Failure evidence is preserved for the Human.
    assert task.qa_verdict is not None
    assert task.qa_verdict.verdict == "fail"
    assert "qa_reported_fail" in (task.qa_failure_reason or "")

    kinds = event_kinds(store, run.id)
    assert kinds.count("task_retry_started") == 1
    assert kinds.count("task_dev_started") == 2
    assert kinds.count("task_qa_failed") == 2
    assert "task_escalated" in kinds
    assert "run_escalated" in kinds
    assert "provider_error" not in kinds

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.ESCALATED
    assert stored.tasks[0].state is TaskState.ESCALATED
    assert stored.tasks[0].attempt == 2

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "qa_reported_fail" in report
    assert "Engine result: **rejected**" in report
