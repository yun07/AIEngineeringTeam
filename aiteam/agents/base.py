"""One throwaway conversation per run, task, attempt and role.

A session owns its own message list and transcript file. It never shares
message objects with another session and never receives a transcript.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aiteam.providers.base import (
    ChatMessage,
    LLMProvider,
    ToolSpec,
    Usage,
)
from aiteam.tools.filesystem import PathDenied


class LimitExceeded(RuntimeError):
    """Raised when a deterministic execution limit is breached."""

    def __init__(self, limit: str) -> None:
        super().__init__(f"{limit} exceeded")
        self.limit = limit


@dataclass
class ToolInvocation:
    name: str
    arguments: dict[str, Any]
    result: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class AgentSession:
    role: str
    model: str
    provider: LLMProvider
    system_prompt: str
    transcript_path: Path
    allowed_tools: frozenset[str]
    max_tool_output_chars: int = 8000
    tool_specs: Sequence[ToolSpec] = field(default_factory=tuple)
    tool_handlers: Mapping[str, Callable[[dict[str, Any]], str]] = field(
        default_factory=dict
    )
    max_turns: int = 12
    max_llm_calls: int = 20
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self._messages: list[ChatMessage] = []
        self.turns = 0
        self.llm_calls = 0
        self.usage = Usage()
        self.tool_invocations: list[ToolInvocation] = []
        with self.transcript_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    {
                        "event": "session_start",
                        "session_id": self.session_id,
                        "role": self.role,
                        "model": self.model,
                        "max_turns": self.max_turns,
                        "max_llm_calls": self.max_llm_calls,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    @property
    def messages(self) -> tuple[ChatMessage, ...]:
        return tuple(self._messages)

    def send(self, user_content: str) -> str:
        """Run the tool loop until the model returns a message without tool calls."""
        self._messages.append(ChatMessage(role="user", content=user_content))
        self._log({"event": "user", "content": user_content})

        while True:
            if self.turns >= self.max_turns:
                raise LimitExceeded("max_turns_per_session")
            if self.llm_calls >= self.max_llm_calls:
                raise LimitExceeded("max_llm_calls_per_task")

            self.turns += 1
            self.llm_calls += 1
            response = self.provider.complete(
                model=self.model,
                system=self.system_prompt,
                messages=tuple(self._messages),
                tools=tuple(self.tool_specs),
            )
            self.usage = self.usage + response.usage
            self._log(
                {
                    "event": "assistant",
                    "text": response.text,
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in response.tool_calls
                    ],
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                }
            )
            self._messages.append(
                ChatMessage(
                    role="assistant",
                    content=response.text,
                    tool_calls=list(response.tool_calls) or None,
                )
            )

            if not response.tool_calls:
                return response.text or ""

            for call in response.tool_calls:
                result, error = self._execute(call.name, call.arguments)
                self.tool_invocations.append(
                    ToolInvocation(
                        name=call.name,
                        arguments=call.arguments,
                        result=result,
                        error=error,
                    )
                )
                self._log(
                    {
                        "event": "tool_result",
                        "name": call.name,
                        "arguments": call.arguments,
                        "result": result,
                        "error": error,
                    }
                )
                self._messages.append(
                    ChatMessage(
                        role="tool",
                        content=result,
                        tool_call_id=call.id,
                        name=call.name,
                    )
                )

    def _execute(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[str, str | None]:
        # The allowlist is enforced at dispatch time, not only by hiding the
        # tool spec, so an unregistered or injected handler stays unreachable.
        if name not in self.allowed_tools:
            message = f"ERROR: tool {name!r} is not permitted for role {self.role}"
            return message, message
        handler = self.tool_handlers.get(name)
        if handler is None:
            message = f"ERROR: tool {name!r} is not available to this role"
            return message, message
        try:
            return self._cap_output(str(handler(arguments))), None
        except PathDenied as exc:
            message = f"ERROR: {exc}"
            return message, message
        except Exception as exc:  # noqa: BLE001 - surfaced to the model as text
            message = f"ERROR: {type(exc).__name__}: {exc}"
            return message, message

    def _cap_output(self, text: str) -> str:
        """Cap the tool result, including the truncation marker, to the limit.

        The returned string never exceeds ``max_tool_output_chars``. The
        detailed marker reports the exact number of characters removed. Marker
        length varies with the digit count of that number, so the largest keep
        length that still fits is found by a binary search rather than a single
        subtraction. A short marker, then a clipped short marker, are the
        fallbacks when the cap is too small for the detailed one.
        """
        limit = self.max_tool_output_chars
        if limit < 1 or len(text) <= limit:
            return text

        total = len(text)

        def marker_for(removed: int) -> str:
            return f"\n...[truncated {removed} characters of tool output]"

        # keep + len(marker_for(total - keep)) grows with keep, so the largest
        # fitting keep can be found by binary search.
        low, high, best = 1, total - 1, 0
        while low <= high:
            middle = (low + high) // 2
            if middle + len(marker_for(total - middle)) <= limit:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        if best >= 1:
            return f"{text[:best]}{marker_for(total - best)}"

        short_marker = "...[truncated]"
        if len(short_marker) < limit:
            keep = limit - len(short_marker)
            return f"{text[:keep]}{short_marker}"
        return short_marker[:limit]

    def _log(self, payload: dict[str, Any]) -> None:
        record = {"session_id": self.session_id, "role": self.role, **payload}
        with self.transcript_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
