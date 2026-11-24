"""Workflow engine: routing, plan validation, Developer write stage and limits."""

from __future__ import annotations

import json

import pytest

from aiteam.engine.workflow import (
    PlanError,
    PlanLimitError,
    next_action,
    parse_plan,
)
from aiteam.models import Action, Run, RunState, Task, TaskState
from aiteam.providers.base import ToolCall, ToolSpec
from aiteam.providers.fake import json_response, text_response, tool_response
from tests.fakes import (
    build_engine,
    event_kinds,
    plan_payload,
    qa_script,
    write_call,
)

SUCCESS_DEVELOPER_SCRIPT = [
    tool_response([write_call("notes.md", "hello\n")]),
    text_response("Wrote notes.md."),
]


def _successful_run(
    tmp_path, *, tasks=1, developer_script=None, qa_scripts=None, **limits
):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(tasks))],
        developer_script=(
            list(developer_script)
            if developer_script is not None
            else SUCCESS_DEVELOPER_SCRIPT
        ),
        qa_script_responses=(
            list(qa_scripts) if qa_scripts is not None else qa_script()
        ),
        **limits,
    )
    run = engine.start("build a demo project")
    result = engine.execute()
    return engine, store, run, result


def test_successful_run_writes_file_logs_events_and_report(tmp_path):
    engine, store, run, result = _successful_run(tmp_path)

    assert result.state is RunState.COMPLETED
    assert result.block_reason is None

    project_file = tmp_path / "repo" / "projects" / "demo" / "notes.md"
    assert project_file.read_text(encoding="utf-8") == "hello\n"

    run_dir = store.run_dir(run.id)
    assert (run_dir / "plan.json").is_file()
    assert (run_dir / "report.md").is_file()
    assert (run_dir / "orchestrator.session.jsonl").is_file()
    assert (run_dir / "task-1.developer.a1.session.jsonl").is_file()

    kinds = event_kinds(store, run.id)
    for expected in (
        "run_created",
        "plan_started",
        "plan_accepted",
        "task_dev_started",
        "task_dev_done",
        "run_completed",
        "report_written",
    ):
        assert expected in kinds
    assert kinds[-1] == "report_written"

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "notes.md" in report
    assert "T1" in report
    assert "max_tasks_per_plan = 3" in report
    assert "## Reporting notes" in report
    assert "no cost figures on purpose" not in report

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.COMPLETED
    assert stored.tasks[0].files_written == ["notes.md"]


def test_developer_session_has_file_tools_only(tmp_path):
    engine, _, _, _ = _successful_run(tmp_path)

    developer_sessions = [
        session for session in engine.sessions if session.role == "developer"
    ]
    assert len(developer_sessions) == 1
    tool_names = {spec.name for spec in developer_sessions[0].tool_specs}
    assert tool_names == {"read_file", "write_file", "list_files"}
    assert "run_command" not in tool_names


def test_each_task_gets_its_own_developer_session(tmp_path):
    engine, store, run, result = _successful_run(
        tmp_path,
        tasks=2,
        developer_script=[
            tool_response([write_call("one.md", "1\n")]),
            text_response("Wrote one.md."),
            tool_response([write_call("two.md", "2\n")]),
            text_response("Wrote two.md."),
        ],
        qa_scripts=qa_script() + qa_script(),
    )

    assert result.state is RunState.COMPLETED
    developer_sessions = [
        session for session in engine.sessions if session.role == "developer"
    ]
    assert len(developer_sessions) == 2
    assert len({session.session_id for session in developer_sessions}) == 2
    run_dir = store.run_dir(run.id)
    assert (run_dir / "task-1.developer.a1.session.jsonl").is_file()
    assert (run_dir / "task-2.developer.a1.session.jsonl").is_file()


def test_task_cap_blocks_the_run_before_any_developer_session(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(4))],
        developer_script=SUCCESS_DEVELOPER_SCRIPT,
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "max_tasks_per_plan" in (result.block_reason or "")
    assert len(engine.sessions) == 1
    assert [session.role for session in engine.sessions] == ["orchestrator"]
    assert (store.run_dir(run.id) / "report.md").is_file()


def test_turn_cap_blocks_the_run(tmp_path):
    looping = [
        tool_response(
            [ToolCall(id=f"call_{index}", name="list_files", arguments={"path": "."})]
        )
        for index in range(10)
    ]
    engine, _, _, result = _successful_run(
        tmp_path,
        developer_script=looping,
        max_turns_per_session=2,
    )

    assert result.state is RunState.BLOCKED
    assert "max_turns_per_session" in (result.block_reason or "")
    assert result.tasks[0].state is TaskState.BLOCKED


def test_llm_call_cap_blocks_the_run(tmp_path):
    script = [
        tool_response([write_call("a.md", "a\n", call_id="call_a")]),
        tool_response([write_call("b.md", "b\n", call_id="call_b")]),
        text_response("done"),
    ]
    engine, _, _, result = _successful_run(
        tmp_path,
        developer_script=script,
        max_llm_calls_per_task=2,
    )

    assert result.state is RunState.BLOCKED
    assert "max_llm_calls_per_task" in (result.block_reason or "")


def test_plan_only_stops_before_the_developer_stage(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER_SCRIPT,
    )
    run = engine.start("build a demo project")
    result = engine.execute(plan_only=True)

    assert result.state is RunState.BLOCKED
    assert "plan_only" in (result.block_reason or "")
    assert len(engine.sessions) == 1
    assert not (tmp_path / "repo" / "projects" / "demo" / "notes.md").exists()
    assert (store.run_dir(run.id) / "plan.json").is_file()


def test_invalid_plan_is_repaired_once(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[
            text_response("not a plan"),
            json_response(plan_payload(1)),
        ],
        developer_script=SUCCESS_DEVELOPER_SCRIPT,
        qa_script_responses=qa_script(),
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.COMPLETED
    assert "plan_invalid" in event_kinds(store, run.id)


def test_second_invalid_plan_blocks_the_run(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[text_response("not a plan"), text_response("still not a plan")],
        developer_script=SUCCESS_DEVELOPER_SCRIPT,
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "plan_invalid" in (result.block_reason or "")
    assert (store.run_dir(run.id) / "report.md").is_file()


def test_parse_plan_rejects_missing_criteria():
    payload = {"tasks": [{"id": "T1", "description": "do it", "acceptance_criteria": []}]}

    with pytest.raises(PlanError, match="at least one acceptance criterion"):
        parse_plan(json.dumps(payload), max_tasks=3)


def test_parse_plan_rejects_duplicate_criterion_ids():
    payload = {
        "tasks": [
            {
                "id": "T1",
                "description": "do it",
                "acceptance_criteria": [
                    {"id": "C1", "text": "first"},
                    {"id": "C1", "text": "second"},
                ],
            }
        ]
    }

    with pytest.raises(PlanError, match="duplicate acceptance criterion"):
        parse_plan(json.dumps(payload), max_tasks=3)


def test_parse_plan_enforces_the_task_cap():
    with pytest.raises(PlanLimitError, match="max_tasks_per_plan"):
        parse_plan(json.dumps(plan_payload(4)), max_tasks=3)


def test_next_action_is_pure_routing():
    run = Run(
        id="run-1",
        project_slug="demo",
        project_root="projects/demo",
        request="build",
        provider="fake",
    )
    assert next_action(run, max_attempts=2) is Action.ORCHESTRATE_PLAN

    run.state = RunState.EXECUTING
    run.tasks = [Task(id="T1", description="write a file")]
    assert next_action(run, max_attempts=2) is Action.RUN_DEVELOPER

    run.tasks[0].state = TaskState.DEV_RUNNING
    assert next_action(run, max_attempts=2) is Action.RUN_QA

    run.tasks[0].state = TaskState.QA_FAILED
    assert next_action(run, max_attempts=2) is Action.RETRY_TASK

    run.tasks[0].attempt = 2
    assert next_action(run, max_attempts=2) is Action.ESCALATE

    run.tasks[0].state = TaskState.ESCALATED
    assert next_action(run, max_attempts=2) is Action.ESCALATE

    run.tasks[0].state = TaskState.DONE
    assert next_action(run, max_attempts=2) is Action.FINALIZE

    # A blocked task is never retried: only an engine-confirmed QA failure
    # routes to retry_task.
    run.tasks[0].state = TaskState.BLOCKED
    assert next_action(run, max_attempts=2) is Action.FINALIZE


def test_provider_failure_during_planning_blocks_the_run_with_report(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[],
        developer_script=[],
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    reason = result.block_reason or ""
    assert "provider_error" in reason
    assert "FakeScriptExhausted" in reason
    assert "planning" in reason

    kinds = event_kinds(store, run.id)
    assert "provider_error" in kinds
    assert kinds[-1] == "run_blocked"

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "provider_error" in report
    assert "FakeScriptExhausted" in report

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.BLOCKED
    assert stored.tasks == []


def test_unclassified_developer_failure_blocks_without_retry(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=[tool_response([write_call("notes.md", "hello\n")])],
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    reason = result.block_reason or ""
    assert "developer_stage_failure_unclassified" in reason
    # Stage attribution only: no ProviderError cause is claimed.
    assert "provider_error" not in reason
    assert "developer task T1" in reason
    task = result.tasks[0]
    assert task.state is TaskState.BLOCKED
    assert task.attempt == 1
    assert task.files_written == ["notes.md"]

    kinds = event_kinds(store, run.id)
    assert "developer_stage_failure_unclassified" in kinds
    assert "provider_error" not in kinds
    assert "task_retry_started" not in kinds
    assert kinds[-1] == "run_blocked"

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "developer_stage_failure_unclassified" in report
    assert "notes.md" in report

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.BLOCKED
    assert stored.tasks[0].state is TaskState.BLOCKED
    assert stored.tasks[0].attempt == 1


def test_developer_cannot_reach_a_forbidden_tool_even_when_registered(
    tmp_path, monkeypatch
):
    executed: list[dict] = []
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=[
            tool_response(
                [
                    ToolCall(
                        id="call_shell",
                        name="run_command",
                        arguments={"argv": ["echo", "hi"]},
                    )
                ]
            ),
            text_response("Could not run a command."),
        ],
        qa_script_responses=qa_script(),
    )

    base_specs = engine._file_tools.tool_specs()
    base_handlers = engine._file_tools.handlers()
    extra_spec = ToolSpec(
        name="run_command",
        description="run a command",
        parameters={"type": "object"},
    )
    monkeypatch.setattr(
        engine._file_tools, "tool_specs", lambda: base_specs + [extra_spec]
    )
    handlers = dict(base_handlers)
    handlers["run_command"] = lambda arguments: executed.append(arguments) or "ran"
    monkeypatch.setattr(engine._file_tools, "handlers", lambda: handlers)

    engine.start("build a demo project")
    result = engine.execute()

    developer = [
        session for session in engine.sessions if session.role == "developer"
    ][0]
    assert {spec.name for spec in developer.tool_specs} == {
        "read_file",
        "write_file",
        "list_files",
    }
    assert executed == []
    assert developer.tool_invocations[0].error is not None
    assert "not permitted" in (developer.tool_invocations[0].error or "")
    assert result.state is RunState.COMPLETED
