"""Fake provider: scripted responses with simulated usage.

Scripts are keyed by role first, then model, so Developer and QA sessions can
never consume each other's scripted responses even when they share a model.
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from aiteam.config import RoleModels
from aiteam.providers.base import (
    ChatMessage,
    LLMResponse,
    ToolCall,
    ToolSpec,
    Usage,
)


class FakeScriptExhausted(RuntimeError):
    """Raised when the fake provider has no scripted response left."""


EXECUTION_ID_PATTERN = re.compile(r"execution_id=([0-9a-zA-Z]+)")


def extract_execution_id(messages: Sequence[ChatMessage]) -> str:
    """Return the last execution id the engine reported in a tool message."""
    for message in reversed(list(messages)):
        if message.role == "tool" and message.content:
            found = EXECUTION_ID_PATTERN.search(message.content)
            if found:
                return found.group(1)
    return ""


ScriptedResponse = LLMResponse | Callable[[Sequence[ChatMessage]], LLMResponse]


@dataclass
class FakeCall:
    role: str
    model: str
    system: str
    messages: list[ChatMessage]
    tools: list[ToolSpec]


class FakeProvider:
    name = "fake"

    def __init__(
        self,
        responses: Sequence[ScriptedResponse] | None = None,
        *,
        by_model: Mapping[str, Iterable[ScriptedResponse]] | None = None,
        by_role: Mapping[str, Iterable[ScriptedResponse]] | None = None,
    ) -> None:
        self._flat: deque[ScriptedResponse] = deque(responses or [])
        self._by_model: dict[str, deque[ScriptedResponse]] = {
            model: deque(script) for model, script in (by_model or {}).items()
        }
        self._by_role: dict[str, deque[ScriptedResponse]] = {
            role: deque(script) for role, script in (by_role or {}).items()
        }
        self.calls: list[FakeCall] = []

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        role: str = "",
    ) -> LLMResponse:
        queue = self._by_role.get(role)
        if queue is None:
            queue = self._by_model.get(model, self._flat)
        if not queue:
            raise FakeScriptExhausted(
                f"no scripted response left for role {role!r} model {model!r}"
            )
        response = queue.popleft()
        if callable(response):
            response = response(messages)
        self.calls.append(
            FakeCall(
                role=role,
                model=model,
                system=system,
                messages=list(messages),
                tools=list(tools),
            )
        )
        return response


def json_response(payload: Any, *, usage: Usage | None = None) -> LLMResponse:
    return LLMResponse(
        text=json.dumps(payload, indent=2),
        usage=usage or Usage(input_tokens=80, output_tokens=40),
    )


def text_response(text: str, *, usage: Usage | None = None) -> LLMResponse:
    return LLMResponse(
        text=text,
        usage=usage or Usage(input_tokens=20, output_tokens=10),
    )


def tool_response(
    calls: Sequence[ToolCall], *, usage: Usage | None = None
) -> LLMResponse:
    return LLMResponse(
        text=None,
        tool_calls=list(calls),
        usage=usage or Usage(input_tokens=60, output_tokens=30),
    )


def demo_by_role(models: RoleModels) -> dict[str, list[LLMResponse]]:
    """Deterministic scripted run used by `python -m aiteam run --fake`.

    Roles are kept apart: the Orchestrator plans, the Developer writes one
    notes file, and QA writes one test file, requests the test command and
    reports a verdict. Nothing is executed without human approval.
    """
    plan = {
        "tasks": [
            {
                "id": "T1",
                "description": "Create a short notes file describing the demo.",
                "acceptance_criteria": [
                    {"id": "C1", "text": "notes.md exists and is not empty."}
                ],
                "constraints": ["Plain text only.", "No execution is required."],
            }
        ]
    }
    developer_write = ToolCall(
        id="call_write_1",
        name="write_file",
        arguments={
            "path": "notes.md",
            "content": (
                "# Demo notes\n\n"
                "This file was written by the Developer session during the M1\n"
                "walking skeleton. The fake provider produced it; no model was\n"
                "called and nothing was executed.\n"
            ),
        },
    )
    qa_write = ToolCall(
        id="call_qa_write_1",
        name="write_file",
        arguments={
            "path": "qa_tests/test_notes.py",
            "content": (
                "from pathlib import Path\n"
                "\n"
                "def test_notes_exists():\n"
                "    assert Path('notes.md').is_file()\n"
                "    assert Path('notes.md').read_text(encoding='utf-8').strip()\n"
                "\n"
                "def test_missing_file_is_rejected():\n"
                "    assert not Path('definitely_missing.md').exists()\n"
            ),
        },
    )
    qa_run = ToolCall(
        id="call_qa_run_1",
        name="run_command",
        arguments={"argv": ["python", "-m", "pytest", "qa_tests", "-q"]},
    )
    verdict = {
        "verdict": "pass",
        "summary": "Both checks passed on the recorded test run.",
        "checks": [
            {
                "criterion": "C1",
                "name": "notes.md exists and is not empty",
                "kind": "positive",
                "command": "python -m pytest qa_tests -q",
                "exit_code": 0,
                "evidence": "2 passed",
                "test_file": "qa_tests/test_notes.py",
            },
            {
                "criterion": "C1",
                "name": "missing file stays absent",
                "kind": "negative",
                "command": "python -m pytest qa_tests -q",
                "exit_code": 0,
                "evidence": "negative check passed",
                "test_file": "qa_tests/test_notes.py",
            },
        ],
        "unverified_requirements": [],
    }

    def verdict_response(messages: Sequence[ChatMessage]) -> LLMResponse:
        execution_id = extract_execution_id(messages)
        payload = json.loads(json.dumps(verdict))
        for check in payload["checks"]:
            check["execution_id"] = execution_id
        return json_response(payload)

    return {
        "orchestrator": [json_response(plan)],
        "developer": [
            tool_response([developer_write]),
            text_response("Wrote notes.md. The task is complete."),
        ],
        "qa": [
            tool_response([qa_write]),
            tool_response([qa_run]),
            verdict_response,
        ],
    }
