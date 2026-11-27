"""OpenAI Chat Completions adapter.

The SDK is imported lazily so the fake-provider test suite works without the
``openai`` package installed. Provider failures are converted into a small
sanitized ``ProviderError`` whose traceback never carries the SDK exception or
a configured secret.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from aiteam.config import Config, validate_live_config
from aiteam.providers.base import (
    ChatMessage,
    LLMResponse,
    ToolCall,
    ToolSpec,
    Usage,
)
from aiteam.secrets import SecretBoundary


# Bounded so a provider cannot flood the audit log with a long message.
DETAIL_TEXT_LIMIT = 200


class ProviderError(RuntimeError):
    """Sanitized provider failure safe to log or persist.

    ``provider_details`` holds a few bounded, already redacted primitives taken
    from the SDK error (status code, request id, provider error type / code /
    message). The raw body, headers, request objects, the SDK exception and its
    traceback are never kept.
    """

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        status_code: Any | None = None,
        provider_details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.provider_details: dict[str, Any] = (
            dict(provider_details) if provider_details else {}
        )

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else self.kind


def _bounded(text: str) -> str:
    """Collapse whitespace and cap the length of one persisted field."""
    collapsed = " ".join(str(text).split())
    if len(collapsed) > DETAIL_TEXT_LIMIT:
        return collapsed[:DETAIL_TEXT_LIMIT] + "..."
    return collapsed


def _extract_provider_details(
    exc: BaseException, boundary: SecretBoundary
) -> dict[str, Any]:
    """Extract a few structured fields from an SDK status error.

    Only primitives leave this function, each already passed through
    ``SecretBoundary.redact()`` and length-bounded. The raw body, headers and
    the exception itself are never returned. Any failure returns at most the
    numeric status code, so the caller keeps its generic safe message.
    """
    details: dict[str, Any] = {}
    try:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and not isinstance(status_code, bool):
            details["status_code"] = status_code

        request_id = getattr(exc, "request_id", None)
        if isinstance(request_id, str) and request_id.strip():
            details["request_id"] = _bounded(boundary.redact(request_id))

        body = getattr(exc, "body", None)
        error_object: Any = None
        if isinstance(body, Mapping):
            candidate = body.get("error")
            error_object = candidate if isinstance(candidate, Mapping) else body

        if isinstance(error_object, Mapping):
            for field in ("type", "code", "message"):
                raw = error_object.get(field)
                if isinstance(raw, bool) or not isinstance(raw, (str, int)):
                    continue
                text = _bounded(str(raw))
                if text:
                    details[f"error_{field}"] = _bounded(boundary.redact(text))
    except Exception:  # noqa: BLE001 - diagnostics must never mask the error
        return {
            key: value
            for key, value in details.items()
            if key == "status_code"
        }
    return details


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


def create_openai_client(
    *, api_key: str, timeout_seconds: int, base_url: str | None = None
) -> Any:
    """Create the SDK client with a lazy import.

    Import failures are returned as a sanitized provider error so a missing
    optional dependency never blocks fake mode and never prints a key.
    ``base_url`` defaults to ``None``, which keeps the SDK's own default
    endpoint, so the OpenAI path is unchanged.
    """
    try:
        import openai  # type: ignore[import-not-found]
    except ImportError:
        error = ProviderError(
            "provider_unavailable",
            "openai package is not installed; install it manually before live mode",
        )
    else:
        return openai.OpenAI(
            api_key=api_key, timeout=timeout_seconds, base_url=base_url
        )

    # Raised outside the except block so __context__ stays empty.
    raise error from None


class OpenAIProvider:
    """Chat Completions adapter for OpenAI and OpenAI-compatible endpoints.

    The request body differs per provider: OpenAI uses
    ``max_completion_tokens`` while DeepSeek uses ``max_tokens`` plus an
    explicit ``thinking`` flag. Only the request assembly branches; mapping,
    error sanitizing and redaction are shared.
    """

    name = "openai"
    SUPPORTED_PROVIDER_NAMES: tuple[str, ...] = ("openai", "deepseek")

    def __init__(
        self,
        client: Any,
        *,
        secret_boundary: SecretBoundary,
        provider_name: str = "openai",
    ) -> None:
        if provider_name not in self.SUPPORTED_PROVIDER_NAMES:
            raise ValueError(
                f"unsupported provider {provider_name!r}; expected one of "
                f"{self.SUPPORTED_PROVIDER_NAMES}"
            )
        if not isinstance(secret_boundary, SecretBoundary):
            raise ValueError(
                "OpenAIProvider requires a SecretBoundary; refusing to create "
                "a provider that could leak SDK error text"
            )
        self._client = client
        self._boundary = secret_boundary
        self.name = provider_name

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
            details = _extract_provider_details(exc, self._boundary)
            safe_message = self._redact(str(exc))
        else:
            return self._map_response(response)

        # Raising outside the except block leaves sys.exc_info() empty, so the
        # new exception has no implicit __context__.
        raise ProviderError(
            kind,
            safe_message,
            status_code=status_code,
            provider_details=details,
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

        if self.name == "deepseek":
            # DeepSeek's OpenAI-compatible endpoint takes ``max_tokens`` and an
            # explicit thinking flag. The installed SDK has no typed kwarg for
            # the flag, so it travels through ``extra_body``; the serialized
            # request body still carries ``thinking``.
            request: dict[str, Any] = {
                "model": model,
                "messages": payload_messages,
                "max_tokens": max_output_tokens,
                "extra_body": {"thinking": {"type": "disabled"}},
            }
        else:
            request = {
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

        choice = choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            # A truncated reply can carry a partial tool-call payload. Mapping
            # it would either hide the truncation or produce a misleading tool
            # error, so the adapter fails closed with the real cause.
            raise ProviderError(
                "output_truncated",
                "provider output hit max_output_tokens; the reply or its tool "
                "arguments may be incomplete",
            )

        message = getattr(choice, "message", None)
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
    """Decode one tool call's arguments.

    Some providers omit the field for a zero-argument call, so a missing or
    empty payload means "no arguments". A non-empty payload that is not a JSON
    object is malformed or truncated; silently returning ``{}`` would hide the
    cause and turn it into a misleading tool error, so it fails closed.
    """
    if isinstance(raw, dict):
        return dict(raw)
    if raw is None:
        return {}
    if not isinstance(raw, str):
        raise ProviderError(
            "tool_arguments_invalid",
            "tool call arguments are not a JSON string",
        )
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        raise ProviderError(
            "tool_arguments_invalid",
            "tool call arguments are not valid JSON; the response was probably "
            "truncated by max_output_tokens",
        ) from None
    if not isinstance(parsed, dict):
        raise ProviderError(
            "tool_arguments_invalid",
            "tool call arguments must decode to a JSON object",
        )
    return parsed


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
            base_url=config.provider.base_url,
        )
    return OpenAIProvider(
        client, secret_boundary=boundary, provider_name=config.provider.name
    )
