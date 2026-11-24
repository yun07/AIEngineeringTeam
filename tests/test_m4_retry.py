"""M4 retry and escalation: bounded, focused checks.

Every infrastructure failure keeps its existing terminal handling. Only an
engine-confirmed QA failure retries, and only a started retry increments the
attempt counter.
"""

from __future__ import annotations

import pytest

from aiteam.cost.guard import BudgetError
from aiteam.engine.handoff import failure_feedback
from aiteam.engine.workflow import WorkflowEngine
from aiteam.models import (
    AcceptanceCriterion,
    QaCheck,
    QaVerdict,
    RunState,
    Task,
    TaskState,
)
from aiteam.providers.fake import (
    FakeProvider,
    json_response,
    text_response,
    tool_response,
)
from aiteam.state.store import StateStore
from aiteam.tools.shell import RunResult
from tests.fakes import (
    ScriptedRunner,
    StubProvider,
    approving_gate,
    build_billing_engine,
    build_engine,
    event_kinds,
    make_config,
    plan_payload,
    qa_script,
    run_demo,
    write_call,
)


# A genuine failing execution, observed by the engine.
FAILED_RUN = RunResult(exit_code=1, stdout="1 failed in 0.01s", stderr="")


class _RaisingProvider:
    """Wrap a provider and raise a chosen error on one chosen call."""

    def __init__(self, inner, *, fail_on_call: int, error: Exception) -> None:
        self.inner = inner
        self.name = getattr(inner, "name", "fake")
        self.fail_on_call = fail_on_call
        self.error = error
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise self.error
        return self.inner.complete(**kwargs)


def _engine_with_provider(tmp_path, provider, **limits):
    config = make_config(**limits)
    store = StateStore(tmp_path / "repo")
    engine = WorkflowEngine(
        config=config,
        provider=provider,
        store=store,
        project_root=tmp_path / "repo" / "projects" / "demo",
        project_slug="demo",
        approval_gate=approving_gate(),
        command_runner=ScriptedRunner(),
    )
    return engine, store


def test_escalation_after_a_single_allowed_attempt_keeps_attempt_at_one(tmp_path):
    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=qa_script(verdict="fail", exit_code=1),
        runner=ScriptedRunner([FAILED_RUN]),
        max_attempts=1,
    )

    assert result.state is RunState.ESCALATED
    assert result.tasks[0].state is TaskState.ESCALATED
    # A failed attempt never increments the counter: only a started retry does.
    assert result.tasks[0].attempt == 1

    kinds = event_kinds(store, run.id)
    assert "task_retry_started" not in kinds
    assert kinds.count("task_dev_started") == 1
    assert kinds.count("task_qa_failed") == 1


def test_budget_error_in_verdict_repair_blocks_without_qa_failed(tmp_path):
    inner = FakeProvider(
        by_role={
            "orchestrator": [json_response(plan_payload(1))],
            "developer": [
                tool_response([write_call("notes.md", "hello\n")]),
                text_response("Wrote notes.md."),
            ],
            # Write the QA test file, run it, then report an invalid verdict so
            # the next call is the repair request.
            "qa": [
                qa_script()[0],
                qa_script()[1],
                json_response({"verdict": "maybe"}),
            ],
        }
    )
    provider = _RaisingProvider(
        inner,
        fail_on_call=7,
        error=BudgetError("budget_exceeded", "budget_exceeded: simulated stop"),
    )
    engine, store = _engine_with_provider(tmp_path, provider)

    run = engine.start("build a demo project")
    result = engine.execute()

    task = result.tasks[0]
    assert result.state is RunState.BLOCKED
    assert task.state is TaskState.BLOCKED
    assert task.state is not TaskState.QA_FAILED
    assert task.attempt == 1
    assert "budget_exceeded" in (result.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_qa_failed" not in kinds
    assert "task_retry_started" not in kinds
    assert kinds[-1] == "run_blocked"


def test_qa_limit_breach_blocks_without_retry(tmp_path):
    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=qa_script(),
        max_llm_calls_per_task=3,
    )

    task = result.tasks[0]
    assert result.state is RunState.BLOCKED
    assert task.state is TaskState.BLOCKED
    assert task.attempt == 1
    assert "max_llm_calls_per_task" in (result.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_retry_started" not in kinds
    assert "task_qa_failed" not in kinds


def test_qa_fail_without_a_failed_execution_blocks_instead_of_retrying(tmp_path):
    # The only scripted execution succeeds (exit code 0), so the reported
    # failure is not backed by any program failure the engine observed.
    _, store, run, result = run_demo(
        tmp_path, qa_script_responses=qa_script(verdict="fail")
    )

    task = result.tasks[0]
    assert result.state is RunState.BLOCKED
    assert task.state is TaskState.BLOCKED
    assert task.state is not TaskState.QA_FAILED
    assert task.attempt == 1
    assert "qa_failure_unsubstantiated" in (result.block_reason or "")
    assert "no_failed_execution_observed" in (result.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_qa_failed" not in kinds
    assert "task_retry_started" not in kinds
    assert kinds[-1] == "run_blocked"


def test_qa_fail_with_unknown_execution_id_blocks(tmp_path):
    # QA cites an execution id the engine never issued.
    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=qa_script(
            verdict="fail", exit_code=1, execution_override="deadbeef"
        ),
        runner=ScriptedRunner([FAILED_RUN]),
    )

    task = result.tasks[0]
    assert result.state is RunState.BLOCKED
    assert task.state is TaskState.BLOCKED
    assert task.attempt == 1
    assert "unknown_execution_id: deadbeef" in (result.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_qa_failed" not in kinds
    assert "task_retry_started" not in kinds


def test_qa_fail_with_mismatched_command_blocks(tmp_path):
    # QA reports a command the engine never executed for that execution id.
    checks = (
        {
            "criterion": "C1",
            "name": "positive check",
            "kind": "positive",
            "command": "python -m pytest qa_tests -v",
            "exit_code": 1,
            "test_file": "qa_tests/test_demo.py",
        },
        {
            "criterion": "C1",
            "name": "negative check",
            "kind": "negative",
            "command": "python -m pytest qa_tests -v",
            "exit_code": 1,
            "test_file": "qa_tests/test_demo.py",
        },
    )
    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=qa_script(verdict="fail", checks=checks, exit_code=1),
        runner=ScriptedRunner([FAILED_RUN]),
    )

    assert result.state is RunState.BLOCKED
    assert result.tasks[0].state is TaskState.BLOCKED
    assert "command_mismatch_for_execution" in (result.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_retry_started" not in kinds


def test_engine_internal_error_stops_automatic_execution(tmp_path, monkeypatch):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=[
            tool_response([write_call("notes.md", "hello\n")]),
            text_response("Wrote notes.md."),
        ],
        qa_script_responses=qa_script(),
    )

    def boom() -> None:
        raise RuntimeError("engine internal failure")

    monkeypatch.setattr(engine, "_handle_qa", boom)

    run = engine.start("build a demo project")
    with pytest.raises(RuntimeError, match="engine internal failure"):
        engine.execute()

    kinds = event_kinds(store, run.id)
    assert "task_retry_started" not in kinds
    assert "run_escalated" not in kinds
    assert "task_escalated" not in kinds

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.EXECUTING
    assert stored.tasks[0].attempt == 1


def test_unclassified_developer_failure_keeps_cost_guard_uncertain(tmp_path):
    inner = StubProvider(
        {"orchestrator": [json_response(plan_payload(1))]},
        name="openai",
    )
    provider = _RaisingProvider(
        inner, fail_on_call=2, error=RuntimeError("provider exploded")
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)

    run = engine.start("build a demo project", budget_usd=1.0)
    result = engine.execute()

    task = result.tasks[0]
    assert result.state is RunState.BLOCKED
    assert task.state is TaskState.BLOCKED
    assert task.attempt == 1
    assert "developer_stage_failure_unclassified" in (task.block_reason or "")
    assert "provider_error" not in (task.block_reason or "")

    kinds = event_kinds(store, run.id)
    assert "task_retry_started" not in kinds
    assert "provider_error" not in kinds

    # Cost Guard accounting is unchanged: the failed call stays uncertain.
    usage = store.read_usage(run.id)
    assert len(usage) == 1
    assert usage[0]["role"] == "orchestrator"
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Usage unavailable: 1 call(s)" in report
    assert "Remaining budget: unknown" in report


def _failed_task() -> Task:
    checks = [
        QaCheck(
            criterion="C1",
            name=f"check {index}",
            kind="positive",
            command="python -m pytest qa_tests -q " + "x" * 400,
            exit_code=1 if index <= 15 else 0,
            evidence="assertion failed: " + "y" * 500,
            test_file=f"qa_tests/test_demo_{index}.py",
        )
        for index in range(1, 16)
    ]
    task = Task(
        id="T1",
        description="write notes",
        acceptance_criteria=[
            AcceptanceCriterion(id="C1", text="notes.md exists.")
        ],
        state=TaskState.QA_FAILED,
    )
    task.qa_verdict = QaVerdict(
        verdict="fail", summary="z" * 500, checks=checks
    )
    task.qa_failure_reason = "exit_code_mismatch: " + "w" * 500
    return task


def test_failure_feedback_is_bounded_and_engine_produced():
    feedback = failure_feedback(_failed_task())

    assert "Failed tests:" in feedback
    assert "Expected behaviour:" in feedback
    assert "- C1: notes.md exists." in feedback
    assert "Actual behaviour:" in feedback
    assert "Relevant error messages:" in feedback
    # Bounded: a capped number of failed checks and clipped fields.
    assert feedback.count("qa_tests/test_demo_") <= 10
    assert max(len(line) for line in feedback.splitlines()) < 500
    assert "w" * 400 not in feedback
    assert "y" * 400 not in feedback


def test_failure_feedback_is_empty_without_a_recorded_failure():
    task = Task(id="T1", description="write notes")
    assert failure_feedback(task) == ""
