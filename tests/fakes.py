"""Fake scripts, simulated usage builders and temporary workspace helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from aiteam.config import Config, Limits, ProviderSettings, RoleModels
from aiteam.engine.workflow import WorkflowEngine
from aiteam.providers.base import LLMResponse, ToolCall, Usage
from aiteam.providers.fake import FakeProvider
from aiteam.state.store import StateStore

DEFAULT_LIMITS: dict[str, int] = {
    "max_tasks_per_plan": 3,
    "max_turns_per_session": 12,
    "max_llm_calls_per_task": 20,
    "max_attempts": 2,
    "command_timeout_seconds": 120,
    "max_tool_output_chars": 8000,
}


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


def build_engine(
    tmp_path: Path,
    *,
    orchestrator_script: Sequence[LLMResponse],
    developer_script: Sequence[LLMResponse] | None = None,
    **limit_overrides: int,
) -> tuple[WorkflowEngine, StateStore]:
    config = make_config(**limit_overrides)
    provider = FakeProvider(
        by_model={
            config.models.orchestrator: list(orchestrator_script),
            config.models.developer: list(developer_script or []),
        }
    )
    store = StateStore(tmp_path / "repo")
    engine = WorkflowEngine(
        config=config,
        provider=provider,
        store=store,
        project_root=tmp_path / "repo" / "projects" / "demo",
        project_slug="demo",
    )
    return engine, store


def event_kinds(store: StateStore, run_id: str) -> list[str]:
    return [event["kind"] for event in store.read_events(run_id)]


def usage(input_tokens: int = 10, output_tokens: int = 5) -> Iterable[Usage]:
    return [Usage(input_tokens=input_tokens, output_tokens=output_tokens)]
