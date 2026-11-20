"""Local token estimation: allowlist, overhead and refusal paths."""

from __future__ import annotations

import pytest

from aiteam.cost import tokens
from aiteam.cost.tokens import (
    TokenEstimationError,
    encoder_for_model,
    estimate_input_tokens,
    estimate_text_tokens,
)
from aiteam.providers.base import ChatMessage, ToolCall, ToolSpec

MODEL = "gpt-4.1-mini"


@pytest.fixture(autouse=True)
def clear_encoder_cache():
    encoder_for_model.cache_clear()
    yield
    encoder_for_model.cache_clear()


def test_supported_model_estimates_text():
    assert estimate_text_tokens(MODEL, "hello world") == 2
    assert estimate_text_tokens(MODEL, "你好世界") > 0


def test_unsupported_model_is_refused_even_if_encoder_exists():
    assert "gpt-3.5-turbo" not in tokens.SUPPORTED_MODELS
    with pytest.raises(TokenEstimationError, match="allowlist"):
        estimate_text_tokens("gpt-3.5-turbo", "hello")


def test_missing_tiktoken_is_refused(monkeypatch):
    def boom():
        raise TokenEstimationError("tiktoken is required for live cost estimation")

    monkeypatch.setattr(tokens, "_tiktoken_module", boom)
    encoder_for_model.cache_clear()

    with pytest.raises(TokenEstimationError, match="tiktoken is required"):
        estimate_text_tokens(MODEL, "hello")


def test_message_overhead_is_counted_per_message():
    one = [ChatMessage(role="user", content="hello")]
    two = one + [ChatMessage(role="assistant", content="ok")]

    first = estimate_input_tokens(model=MODEL, system="sys", messages=one)
    second = estimate_input_tokens(model=MODEL, system="sys", messages=two)

    assert second - first >= tokens.MESSAGE_OVERHEAD_TOKENS


def test_tool_schemas_are_counted():
    tools = [
        ToolSpec(
            name="write_file",
            description="write a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
    ]

    without_tools = estimate_input_tokens(
        model=MODEL, system="sys", messages=[ChatMessage(role="user", content="hi")]
    )
    with_tools = estimate_input_tokens(
        model=MODEL,
        system="sys",
        messages=[ChatMessage(role="user", content="hi")],
        tools=tools,
    )

    assert with_tools > without_tools


def test_tool_call_arguments_are_counted():
    small = ChatMessage(
        role="assistant",
        content=None,
        tool_calls=[ToolCall(id="1", name="write_file", arguments={"path": "a.txt"})],
    )
    large = ChatMessage(
        role="assistant",
        content=None,
        tool_calls=[
            ToolCall(
                id="1",
                name="write_file",
                arguments={"path": "a.txt", "content": "x" * 400},
            )
        ],
    )

    small_tokens = estimate_input_tokens(model=MODEL, system="sys", messages=[small])
    large_tokens = estimate_input_tokens(model=MODEL, system="sys", messages=[large])

    assert large_tokens > small_tokens


def test_non_string_content_is_refused():
    broken = ChatMessage(role="user", content=123)

    with pytest.raises(TokenEstimationError, match="content must be a string"):
        estimate_input_tokens(model=MODEL, system="sys", messages=[broken])
