"""Retry then pass scenario: one QA failure, one retry, then acceptance."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from aiteam.providers.fake import text_response, tool_response
from tests.fakes import event_kinds, qa_script, run_demo, write_call

# Two full Developer attempts: the retry writes the file again.
TWO_ATTEMPT_DEVELOPER = [
    tool_response([write_call("notes.md", "first attempt\n")]),
    text_response("Wrote notes.md."),
    tool_response(
        [write_call("notes.md", "second attempt\n", call_id="call_retry_1")]
    ),
    text_response("Rewrote notes.md after the QA feedback."),
]

FEEDBACK_MARKERS = (
    "Previous attempt feedback",
    "Failed tests",
    "Expected behaviour",
    "Actual behaviour",
    "Relevant error messages",
    "qa_reported_fail",
)


def test_first_qa_failure_retries_once_then_passes(tmp_path):
    engine, store, run, result = run_demo(
        tmp_path,
        developer_script=TWO_ATTEMPT_DEVELOPER,
        qa_script_responses=qa_script(verdict="fail") + qa_script(),
    )

    assert result.state is RunState.COMPLETED
    task = result.tasks[0]
    assert task.state is TaskState.DONE
    assert task.attempt == 2

    kinds = event_kinds(store, run.id)
    assert kinds.count("task_retry_started") == 1
    assert kinds.count("task_dev_started") == 2
    assert kinds.count("task_qa_failed") == 1
    assert kinds.count("task_qa_passed") == 1
    assert "run_escalated" not in kinds
    assert "provider_error" not in kinds

    events = store.read_events(run.id)
    attempt_sequence = [
        event["data"]["attempt"]
        for event in events
        if event["kind"] == "task_dev_started"
    ]
    assert attempt_sequence == [1, 2]

    # AI call accounting accumulates across attempts and is never reset.
    developer_sessions = [item for item in engine.sessions if item.role == "developer"]
    qa_sessions = [item for item in engine.sessions if item.role == "qa"]
    assert [item.llm_calls for item in developer_sessions] == [2, 2]
    assert [item.llm_calls for item in qa_sessions] == [3, 3]
    assert task.llm_calls == sum(
        item.llm_calls for item in developer_sessions + qa_sessions
    )

    # The retried Developer session receives bounded engine feedback only.
    developer_calls = [
        call for call in engine._provider.calls if call.role == "developer"
    ]
    first_bundle = developer_calls[0].messages[0].content
    retry_bundle = developer_calls[2].messages[0].content
    assert "Previous attempt feedback" not in first_bundle
    for marker in FEEDBACK_MARKERS:
        assert marker in retry_bundle
    # No transcript and no QA test source leaks into the bundle.
    assert "def test_positive" not in retry_bundle
    assert len(retry_bundle) - len(first_bundle) < 2000
