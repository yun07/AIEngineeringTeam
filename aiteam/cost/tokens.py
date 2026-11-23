"""Local token estimation for budget preflight only.

``tiktoken`` gives a local estimate. It is not a promise about provider
billing: cached tokens, reasoning tokens, framing differences and price
changes can all make the final invoice differ from this estimate.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Sequence

# Only explicitly listed models may be priced and estimated. A successful
# ``encoding_for_model`` call is not treated as proof that a model is valid.
SUPPORTED_MODELS: frozenset[str] = frozenset(
    {"gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "deepseek-flash"}
)

# Models tiktoken cannot map by name get an explicit encoding. ``cl100k_base``
# is used for DeepSeek as a local estimation proxy only: it is a neighbouring
# vocabulary, not the provider's own tokenizer, so counts are approximate.
MODEL_ENCODINGS: dict[str, str] = {"deepseek-flash": "cl100k_base"}

# Conservative framing overhead, not billed-token knowledge.
MESSAGE_OVERHEAD_TOKENS = 4
REPLY_PRIMING_TOKENS = 3


class TokenEstimationError(ValueError):
    """Raised when a request cannot be estimated reliably."""


def _tiktoken_module() -> Any:
    try:
        import tiktoken  # imported lazily so the rest of the engine works
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise TokenEstimationError(
            "tiktoken is required for live cost estimation; install it manually"
        ) from exc
    return tiktoken


@lru_cache(maxsize=8)
def encoder_for_model(model: str) -> Any:
    if model not in SUPPORTED_MODELS:
        raise TokenEstimationError(
            f"model {model!r} is not in the supported allowlist "
            f"{sorted(SUPPORTED_MODELS)}"
        )
    tiktoken = _tiktoken_module()
    explicit = MODEL_ENCODINGS.get(model)
    if explicit is not None:
        try:
            return tiktoken.get_encoding(explicit)
        except (KeyError, ValueError) as exc:
            raise TokenEstimationError(
                f"tiktoken has no encoding named {explicit!r} "
                f"configured for model {model!r}"
            ) from exc
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError as exc:
        raise TokenEstimationError(
            f"tiktoken has no encoder for model {model!r}"
        ) from exc


def estimate_text_tokens(model: str, text: str) -> int:
    if not isinstance(text, str):
        raise TokenEstimationError("text to estimate must be a string")
    return len(encoder_for_model(model).encode(text))


def _count_message(model: str, message: Any) -> int:
    total = MESSAGE_OVERHEAD_TOKENS
    content = getattr(message, "content", None)
    if content is not None:
        if not isinstance(content, str):
            raise TokenEstimationError("message content must be a string or None")
        total += estimate_text_tokens(model, content)
    for call in getattr(message, "tool_calls", None) or []:
        total += estimate_text_tokens(model, str(call.name))
        try:
            arguments = json.dumps(call.arguments, sort_keys=True, separators=(",", ":"))
        except TypeError as exc:
            raise TokenEstimationError(
                "tool call arguments must be JSON serializable"
            ) from exc
        total += estimate_text_tokens(model, arguments)
    name = getattr(message, "name", None)
    if name:
        total += estimate_text_tokens(model, str(name))
    return total


def _count_tools(model: str, tools: Sequence[Any]) -> int:
    if not tools:
        return 0
    payload = [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in tools
    ]
    try:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise TokenEstimationError("tool schemas must be JSON serializable") from exc
    return estimate_text_tokens(model, serialized)


def estimate_input_tokens(
    *,
    model: str,
    system: str,
    messages: Sequence[Any],
    tools: Sequence[Any] = (),
) -> int:
    """Estimate input tokens for one call. This is an estimate, not usage."""
    if not isinstance(system, str):
        raise TokenEstimationError("system prompt must be a string")
    total = REPLY_PRIMING_TOKENS
    total += estimate_text_tokens(model, system)
    total += _count_tools(model, tools)
    for message in messages:
        total += _count_message(model, message)
    return total
