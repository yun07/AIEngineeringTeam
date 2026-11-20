"""Fake provider: scripted responses with simulated usage.

Every limit is testable without a paid call because the scripted responses
carry usage counts and can return tool calls forever.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

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


@dataclass
class FakeCall:
    model: str
    system: str
    messages: list[ChatMessage]
    tools: list[ToolSpec]


class FakeProvider:
    name = "fake"

    def __init__(
        self,
        responses: Sequence[LLMResponse] | None = None,
        *,
        by_model: Mapping[str, Iterable[LLMResponse]] | None = None,
    ) -> None:
        self._flat: deque[LLMResponse] = deque(responses or [])
        self._by_model: dict[str, deque[LLMResponse]] = {
            model: deque(script) for model, script in (by_model or {}).items()
        }
        self.calls: list[FakeCall] = []

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> LLMResponse:
        queue = self._by_model.get(model, self._flat)
        if not queue:
            raise FakeScriptExhausted(f"no scripted response left for model {model!r}")
        response = queue.popleft()
        self.calls.append(
            FakeCall(
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


def demo_by_model(models: RoleModels) -> dict[str, list[LLMResponse]]:
    """Deterministic scripted run used by `python -m aiteam run --fake`.

    One task is planned, then the developer writes a single notes file. No code
    is executed and no file outside projects/<slug>/ is touched.
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
    write = ToolCall(
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
    return {
        models.orchestrator: [json_response(plan)],
        models.developer: [
            tool_response([write]),
            text_response("Wrote notes.md. The task is complete."),
        ],
    }
