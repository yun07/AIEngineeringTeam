"""Fake scripts, simulated usage builders and temporary workspace helpers."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from aiteam.config import (
    Config,
    CostSettings,
    Limits,
    ProviderSettings,
    RoleModels,
)
from aiteam.engine.policy import ApprovalGate
from aiteam.engine.workflow import WorkflowEngine
from aiteam.providers.base import LLMResponse, ToolCall, Usage
from aiteam.providers.fake import (
    FakeProvider,
    FakeScriptExhausted,
    extract_execution_id,
    json_response,
    text_response,
    tool_response,
)
from aiteam.state.store import StateStore
from aiteam.tools.shell import RunResult

DEFAULT_LIMITS: dict[str, int] = {
    "max_tasks_per_plan": 3,
    "max_turns_per_session": 12,
    "max_llm_calls_per_task": 20,
    "max_attempts": 2,
    "command_timeout_seconds": 120,
    "max_tool_output_chars": 8000,
}

TEST_COMMAND = "python -m pytest qa_tests -q"
DEFAULT_TEST_CONTENT = (
    "def test_positive():\n"
    "    assert True\n"
    "\n"
    "\n"
    "def test_negative():\n"
    "    assert not False\n"
)


class ScriptedRunner:
    """Deterministic command runner for engine scenarios."""

    def __init__(
        self,
        results: Sequence[RunResult] | None = None,
        *,
        default_exit_code: int = 0,
    ) -> None:
        self._results = list(results or [])
        self._default_exit_code = default_exit_code
        self.calls: list[dict[str, Any]] = []

    def run(self, *, argv, cwd, env, timeout) -> RunResult:
        self.calls.append(
            {
                "argv": list(argv),
                "cwd": str(cwd),
                "env": dict(env),
                "timeout": timeout,
            }
        )
        if self._results:
            return self._results.pop(0)
        return RunResult(
            exit_code=self._default_exit_code,
            stdout="1 passed in 0.01s",
            stderr="",
        )


SUPPORTED_TEST_MODEL = "gpt-4.1-mini"
TEST_PRICING: dict[str, dict[str, float]] = {
    SUPPORTED_TEST_MODEL: {"input_per_mtok": 0.4, "output_per_mtok": 1.6}
}


class StubProvider:
    """Billable-shape test double with explicit, caller-controlled usage.

    ``name`` defaults to a non-fake identity so billing tests keep exercising
    the live branch. Pass ``name="fake"`` when a test needs a non-billable
    provider in fake mode (the engine refuses to mix the two).
    """

    def __init__(
        self,
        responses: Mapping[str, Sequence[LLMResponse]],
        *,
        error: Exception | None = None,
        name: str = "stub",
    ) -> None:
        self._queues: dict[str, deque[LLMResponse]] = {
            role: deque(script) for role, script in responses.items()
        }
        self.error = error
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[Any],
        tools: Sequence[Any],
        role: str = "",
        max_output_tokens: int = 0,
    ) -> LLMResponse:
        self.calls.append(
            {
                "model": model,
                "role": role,
                "max_output_tokens": max_output_tokens,
                "messages": list(messages),
                "tools": list(tools),
            }
        )
        if self.error is not None:
            raise self.error
        queue = self._queues.get(role)
        if not queue:
            raise FakeScriptExhausted(f"no stub response left for role {role!r}")
        return queue.popleft()


def make_billing_config(**limit_overrides: int) -> Config:
    limits = Limits(**{**DEFAULT_LIMITS, **limit_overrides})
    return Config(
        provider=ProviderSettings(name="openai"),
        models=RoleModels(
            orchestrator=SUPPORTED_TEST_MODEL,
            developer=SUPPORTED_TEST_MODEL,
            qa=SUPPORTED_TEST_MODEL,
        ),
        limits=limits,
        cost=CostSettings(
            max_output_tokens_per_call=1200,
            safety_margin_percent=10.0,
            max_context_tokens=120000,
            estimator="tiktoken",
        ),
        pricing=TEST_PRICING,
    )


def build_billing_engine(
    tmp_path: Path,
    *,
    provider: Any,
    **limit_overrides: int,
):
    config = make_billing_config(**limit_overrides)
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


def approving_gate() -> ApprovalGate:
    return ApprovalGate(approver=lambda prompt: True, interactive=True)


def denying_gate() -> ApprovalGate:
    return ApprovalGate(approver=lambda prompt: False, interactive=True)


def make_config(**limit_overrides: int) -> Config:
    limits = Limits(**{**DEFAULT_LIMITS, **limit_overrides})
    return Config(
        provider=ProviderSettings(name="fake"),
        models=RoleModels(
            orchestrator="fake-orchestrator",
            developer="fake-developer",
            qa="fake-qa",
        ),
        limits=limits,
    )


def plan_payload(task_count: int = 1) -> dict[str, Any]:
    tasks = []
    for index in range(1, task_count + 1):
        tasks.append(
            {
                "id": f"T{index}",
                "description": f"Create file number {index}.",
                "acceptance_criteria": [
                    {"id": "C1", "text": f"file_{index}.md exists and is not empty."}
                ],
                "constraints": ["Plain text only."],
            }
        )
    return {"tasks": tasks}


def write_call(path: str, content: str = "hello\n", call_id: str = "call_1") -> ToolCall:
    return ToolCall(
        id=call_id,
        name="write_file",
        arguments={"path": path, "content": content},
    )


def qa_script(
    *,
    checks: Sequence[Mapping[str, Any]] | None = None,
    exit_code: int = 0,
    test_file: str = "qa_tests/test_demo.py",
    test_content: str = DEFAULT_TEST_CONTENT,
    command: str = TEST_COMMAND,
    verdict: str = "pass",
    run_call_id: str = "qa_run_1",
    write_call_id: str = "qa_write_1",
    execution_override: str | None = None,
) -> list[LLMResponse]:
    """Build the three scripted QA turns: write tests, run, report verdict."""
    if checks is None:
        checks = (
            {
                "criterion": "C1",
                "name": "positive check",
                "kind": "positive",
                "exit_code": exit_code,
                "test_file": test_file,
            },
            {
                "criterion": "C1",
                "name": "negative check",
                "kind": "negative",
                "exit_code": exit_code,
                "test_file": test_file,
            },
        )
    base_payload = {
        "verdict": verdict,
        "summary": "recorded checks",
        "checks": [
            {"command": command, "evidence": "1 passed", **dict(check)}
            for check in checks
        ],
        "unverified_requirements": [],
    }

    def verdict_response(messages) -> LLMResponse:
        import json as _json

        payload = _json.loads(_json.dumps(base_payload))
        execution_id = (
            execution_override
            if execution_override is not None
            else extract_execution_id(messages)
        )
        for check in payload["checks"]:
            check["execution_id"] = execution_id
        return json_response(payload)

    return [
        tool_response(
            [
                ToolCall(
                    id=write_call_id,
                    name="write_file",
                    arguments={"path": test_file, "content": test_content},
                )
            ]
        ),
        tool_response(
            [
                ToolCall(
                    id=run_call_id,
                    name="run_command",
                    arguments={"argv": command.split()},
                )
            ]
        ),
        verdict_response,
    ]


def build_engine(
    tmp_path: Path,
    *,
    orchestrator_script: Sequence[LLMResponse],
    developer_script: Sequence[LLMResponse] | None = None,
    qa_script_responses: Sequence[LLMResponse] | None = None,
    gate: ApprovalGate | None = None,
    runner: Any | None = None,
    **limit_overrides: int,
) -> tuple[WorkflowEngine, StateStore]:
    config = make_config(**limit_overrides)
    provider = FakeProvider(
        by_role={
            "orchestrator": list(orchestrator_script),
            "developer": list(developer_script or []),
            "qa": list(qa_script_responses or []),
        }
    )
    store = StateStore(tmp_path / "repo")
    engine = WorkflowEngine(
        config=config,
        provider=provider,
        store=store,
        project_root=tmp_path / "repo" / "projects" / "demo",
        project_slug="demo",
        approval_gate=gate or approving_gate(),
        command_runner=runner or ScriptedRunner(),
    )
    return engine, store


SUCCESS_DEVELOPER: list[LLMResponse] = [
    tool_response([write_call("notes.md", "hello\n")]),
    text_response("Wrote notes.md."),
]


def run_demo(
    tmp_path: Path,
    *,
    qa_script_responses: Sequence[LLMResponse],
    gate: ApprovalGate | None = None,
    runner: Any | None = None,
    plan: Mapping[str, Any] | None = None,
    developer_script: Sequence[LLMResponse] | None = None,
    **limit_overrides: int,
):
    """Run one full engine execution with scripted roles."""
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan or plan_payload(1))],
        developer_script=list(developer_script or SUCCESS_DEVELOPER),
        qa_script_responses=qa_script_responses,
        gate=gate,
        runner=runner,
        **limit_overrides,
    )
    run = engine.start("build a demo project")
    result = engine.execute()
    return engine, store, run, result


def event_kinds(store: StateStore, run_id: str) -> list[str]:
    return [event["kind"] for event in store.read_events(run_id)]


def usage(input_tokens: int = 10, output_tokens: int = 5) -> Usage:
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)


__all__ = [
    "DEFAULT_TEST_CONTENT",
    "SUCCESS_DEVELOPER",
    "SUPPORTED_TEST_MODEL",
    "ScriptedRunner",
    "StubProvider",
    "TEST_COMMAND",
    "TEST_PRICING",
    "approving_gate",
    "build_billing_engine",
    "build_engine",
    "denying_gate",
    "event_kinds",
    "json_response",
    "make_billing_config",
    "make_config",
    "plan_payload",
    "qa_script",
    "run_demo",
    "text_response",
    "tool_response",
    "usage",
    "write_call",
]
