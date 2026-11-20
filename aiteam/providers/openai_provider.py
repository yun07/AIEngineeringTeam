"""OpenAI Chat Completions adapter.

The SDK is imported lazily so the fake-provider test suite works without the
``openai`` package installed. Provider failures are converted into a small
sanitized ``ProviderError`` whose traceback never carries the SDK exception or
a configured secret.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from aiteam.config import Config, validate_live_config
from aiteam.providers.base import (
    ChatMessage,
    LLMResponse,
    ToolCall,
    ToolSpec,
    Usage,
)
from aiteam.secrets import SecretBoundary


class ProviderError(RuntimeError):
    """Sanitized provider failure safe to log or persist."""

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        status_code: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else self.kind


def _classify_exception(exc: BaseException) -> str:
    name = type(exc).__name__
    if name == "APITimeoutError":
        return "timeout"
    if name == "AuthenticationError":
        return "authentication"
    if name == "RateLimitError":
        return "rate_limit"
    if name == "APIStatusError":
        code = getattr(exc, "status_code", None)
        return f"api_status_{code}" if code is not None else "api_status"
    if name == "APIConnectionError":
        return "connection"
    return "api_error"


def create_openai_client(*, api_key: str, timeout_seconds: int) -> Any:
    """Create the SDK client with a lazy import.

    Import failures are returned as a sanitized provider error so a missing
    optional dependency never blocks fake mode and never prints a key.
    """
    try:
        import openai  # type: ignore[import-not-found]
    except ImportError:
        error = ProviderError(
            "provider_unavailable",
            "openai package is not installed; install it manually before live mode",
        )
    else:
        return openai.OpenAI(api_key=api_key, timeout=timeout_seconds)

    # Raised outside the except block so __context__ stays empty.
    raise error from None


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        client: Any,
        *,
        secret_boundary: SecretBoundary,
    ) -> None:
        if not isinstance(secret_boundary, SecretBoundary):
            raise ValueError(
                "OpenAIProvider requires a SecretBoundary; refusing to create "
                "a provider that could leak SDK error text"
            )
        self._client = client
        self._boundary = secret_boundary

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        role: str = "",
        max_output_tokens: int = 0,
    ) -> LLMResponse:
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
        ):
            raise ValueError("max_output_tokens must be a positive integer")

        request = self._build_request(
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_output_tokens=max_output_tokens,
        )
        try:
            response = self._client.chat.completions.create(**request)
        except Exception as exc:
            # Extract primitives only. The SDK exception is not stored,
            # chained or referenced after this block.
            kind = _classify_exception(exc)
            status_code = getattr(exc, "status_code", None)
            safe_message = self._redact(str(exc))
        else:
            return self._map_response(response)

        # Raising outside the except block leaves sys.exc_info() empty, so the
        # new exception has no implicit __context__.
        raise ProviderError(
            kind, safe_message, status_code=status_code
        ) from None

    def _build_request(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        payload_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system}
        ]
        for message in messages:
            payload_messages.append(self._message_payload(message))

        request: dict[str, Any] = {
            "model": model,
            "messages": payload_messages,
            "max_completion_tokens": max_output_tokens,
        }
        if tools:
            request["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
        return request

    @staticmethod
    def _message_payload(message: ChatMessage) -> dict[str, Any]:
        if message.role == "assistant" and message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(
                                call.arguments, ensure_ascii=False
                            ),
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        if message.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id or "",
                "content": message.content or "",
            }
        return {
            "role": message.role,
            "content": message.content if message.content is not None else "",
        }

    def _map_response(self, response: Any) -> LLMResponse:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return LLMResponse(
                text=None, tool_calls=[], usage=self._map_usage(response)
            )

        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None) if message is not None else None
        tool_calls: list[ToolCall] = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            name = getattr(function, "name", "") if function is not None else ""
            raw_arguments = (
                getattr(function, "arguments", "{}")
                if function is not None
                else "{}"
            )
            arguments = _parse_arguments(raw_arguments)
            tool_calls.append(
                ToolCall(
                    id=str(getattr(call, "id", "")),
                    name=str(name),
                    arguments=arguments,
                )
            )
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=self._map_usage(response),
        )

    @staticmethod
    def _map_usage(response: Any) -> Usage | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        input_tokens = getattr(usage, "prompt_tokens", None)
        if input_tokens is None:
            input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        if output_tokens is None:
            output_tokens = getattr(usage, "output_tokens", None)
        if (
            isinstance(input_tokens, bool)
            or not isinstance(input_tokens, int)
            or isinstance(output_tokens, bool)
            or not isinstance(output_tokens, int)
        ):
            return None
        return Usage(input_tokens=input_tokens, output_tokens=output_tokens)

    def _redact(self, text: str) -> str:
        return self._boundary.redact(text)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def create_openai_provider(
    config: Config,
    api_key: str,
    *,
    boundary: SecretBoundary,
    client: Any | None = None,
) -> OpenAIProvider:
    """Validate live configuration and build the adapter.

    Validation is repeated here as defence in depth; the CLI also calls it
    before resolving a key or creating a client.
    """
    if not isinstance(boundary, SecretBoundary):
        raise ValueError(
            "create_openai_provider requires a SecretBoundary before a client "
            "can be created"
        )
    validate_live_config(config)
    if not api_key:
        raise ProviderError(
            "authentication",
            "an API key is required for live mode",
        )
    if client is None:
        client = create_openai_client(
            api_key=api_key,
            timeout_seconds=config.provider.timeout_seconds,
        )
    return OpenAIProvider(client, secret_boundary=boundary)
