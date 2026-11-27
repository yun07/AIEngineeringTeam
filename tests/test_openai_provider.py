"""OpenAI adapter mapping, usage handling and sanitized exception chaining."""

from __future__ import annotations

import builtins
import traceback
from dataclasses import replace
from types import SimpleNamespace

import pytest

from aiteam.config import ConfigError, ProviderSettings
from aiteam.providers.base import ChatMessage, ToolCall, ToolSpec
from aiteam.providers.openai_provider import (
    OpenAIProvider,
    ProviderError,
    create_openai_client,
    create_openai_provider,
)
from aiteam.secrets import SecretBoundary
from tests.fakes import make_billing_config

DUMMY_KEY = "sk-dummy-provider-boundary-key"


class FakeCompletions:
    def __init__(self, response=None, error: BaseException | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error: BaseException | None = None) -> None:
        self.completions = FakeCompletions(response, error)
        self.chat = SimpleNamespace(completions=self.completions)


class APITimeoutError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class RateLimitError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class APIStatusError(Exception):
    def __init__(self, message: str, status_code: int = 429) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response(*, text="hello", tool_calls=None, usage=True, finish_reason=None):
    usage_value = (
        SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        if usage is True
        else usage
    )
    message = SimpleNamespace(content=text, tool_calls=tool_calls or [])
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=message, finish_reason=finish_reason)
        ],
        usage=usage_value,
    )


def _spec() -> ToolSpec:
    return ToolSpec(
        name="write_file",
        description="write a file",
        parameters={"type": "object"},
    )


def _provider(client):
    return OpenAIProvider(
        client, secret_boundary=SecretBoundary([DUMMY_KEY])
    )


def test_messages_tools_and_max_completion_tokens_are_mapped():
    client = FakeClient(_response(text="done"))
    provider = _provider(client)

    result = provider.complete(
        model="gpt-4.1-mini",
        system="system text",
        messages=[
            ChatMessage(role="user", content="hello"),
            ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="write_file",
                        arguments={"path": "notes.md"},
                    )
                ],
            ),
            ChatMessage(
                role="tool",
                content="ok",
                tool_call_id="call_1",
                name="write_file",
            ),
        ],
        tools=[_spec()],
        max_output_tokens=32,
    )

    request = client.completions.requests[0]
    assert request["model"] == "gpt-4.1-mini"
    assert request["max_completion_tokens"] == 32
    assert request["messages"][0] == {"role": "system", "content": "system text"}
    assert request["messages"][1] == {"role": "user", "content": "hello"}
    assert request["messages"][2]["tool_calls"][0]["function"] == {
        "name": "write_file",
        "arguments": '{"path": "notes.md"}',
    }
    assert request["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "ok",
    }
    assert request["tools"][0]["type"] == "function"
    assert request["tools"][0]["function"]["name"] == "write_file"
    assert result.text == "done"


def test_empty_tools_are_omitted():
    client = FakeClient(_response())
    provider = _provider(client)

    provider.complete(
        model="gpt-4.1-mini",
        system="system",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=10,
    )

    assert "tools" not in client.completions.requests[0]


@pytest.mark.parametrize("value", [0, -1, True])
def test_non_positive_max_output_tokens_is_refused(value):
    provider = _provider(FakeClient(_response()))

    with pytest.raises(ValueError, match="max_output_tokens"):
        provider.complete(
            model="gpt-4.1-mini",
            system="system",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[],
            max_output_tokens=value,
        )


def test_response_text_tool_calls_and_usage_are_mapped():
    tool_call = SimpleNamespace(
        id="call_9",
        function=SimpleNamespace(
            name="write_file", arguments='{"path": "a.txt", "content": "x"}'
        ),
    )
    client = FakeClient(_response(text="result", tool_calls=[tool_call]))
    result = _provider(client).complete(
        model="gpt-4.1-mini",
        system="system",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=10,
    )

    assert result.text == "result"
    assert result.tool_calls[0].id == "call_9"
    assert result.tool_calls[0].arguments == {"path": "a.txt", "content": "x"}
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_empty_tool_arguments_are_an_empty_mapping():
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="write_file", arguments=""),
    )
    client = FakeClient(_response(text=None, tool_calls=[tool_call]))

    result = _provider(client).complete(
        model="gpt-4.1-mini",
        system="system",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=10,
    )

    assert result.tool_calls[0].arguments == {}


def test_invalid_tool_arguments_fail_closed():
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="write_file", arguments="{not json"),
    )
    client = FakeClient(_response(text=None, tool_calls=[tool_call]))

    with pytest.raises(ProviderError) as info:
        _provider(client).complete(
            model="gpt-4.1-mini",
            system="system",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[],
            max_output_tokens=10,
        )

    assert info.value.kind == "tool_arguments_invalid"


def test_finish_reason_length_raises_output_truncated():
    client = FakeClient(_response(text=None, finish_reason="length"))

    with pytest.raises(ProviderError) as info:
        _provider(client).complete(
            model="gpt-4.1-mini",
            system="system",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[],
            max_output_tokens=10,
        )

    assert info.value.kind == "output_truncated"


def test_missing_usage_is_none_not_zero():
    client = FakeClient(_response(usage=None))

    result = _provider(client).complete(
        model="gpt-4.1-mini",
        system="system",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=10,
    )

    assert result.usage is None


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (APITimeoutError("timeout"), "timeout"),
        (AuthenticationError("bad key"), "authentication"),
        (RateLimitError("slow down"), "rate_limit"),
        (APIStatusError("status", status_code=429), "api_status_429"),
        (APIConnectionError("down"), "connection"),
        (RuntimeError("other"), "api_error"),
    ],
)
def test_provider_errors_are_classified(error, kind):
    provider = _provider(FakeClient(error=error))

    with pytest.raises(ProviderError) as info:
        provider.complete(
            model="gpt-4.1-mini",
            system="system",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[],
            max_output_tokens=10,
        )

    assert info.value.kind == kind


def test_provider_error_has_no_exception_chain_and_no_key():
    key = "sk-dummy-secret-for-chain-test"
    boundary = SecretBoundary([key])
    error = APITimeoutError(f"request failed with {key}")

    provider = OpenAIProvider(FakeClient(error=error), secret_boundary=boundary)

    with pytest.raises(ProviderError) as info:
        provider.complete(
            model="gpt-4.1-mini",
            system="system",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[],
            max_output_tokens=10,
        )

    raised = info.value
    assert raised.kind == "timeout"
    assert raised.__cause__ is None
    assert raised.__context__ is None
    assert raised.__suppress_context__ is True
    formatted = "".join(
        traceback.format_exception(type(raised), raised, raised.__traceback__)
    )
    assert key not in formatted
    assert key not in str(raised)


def test_provider_construction_without_boundary_is_refused():
    client = FakeClient(error=APITimeoutError(f"leak {DUMMY_KEY}"))

    with pytest.raises(TypeError):
        OpenAIProvider(client)

    with pytest.raises(ValueError, match="SecretBoundary"):
        OpenAIProvider(client, secret_boundary=None)


def test_factory_requires_a_boundary_before_using_the_client():
    client = FakeClient(_response())

    with pytest.raises(ValueError, match="SecretBoundary"):
        create_openai_provider(
            make_billing_config(),
            "dummy-key",
            boundary=None,
            client=client,
        )

    assert client.completions.requests == []


def test_factory_validates_before_returning_a_provider():
    config = make_billing_config()
    client = FakeClient(_response())

    provider = create_openai_provider(
        config,
        "dummy-key",
        boundary=SecretBoundary([DUMMY_KEY]),
        client=client,
    )

    assert provider.name == "openai"


def test_factory_refuses_invalid_live_config():
    config = replace(
        make_billing_config(), provider=ProviderSettings(name="other")
    )

    with pytest.raises(ConfigError, match="live provider must be one of"):
        create_openai_provider(
            config,
            "dummy-key",
            boundary=SecretBoundary([DUMMY_KEY]),
            client=FakeClient(_response()),
        )


def test_import_failure_has_no_exception_chain(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("openai is missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ProviderError) as info:
        create_openai_client(api_key="dummy-key", timeout_seconds=10)

    raised = info.value
    assert raised.kind == "provider_unavailable"
    assert raised.__cause__ is None
    assert raised.__context__ is None
    assert raised.__suppress_context__ is True
    assert "dummy-key" not in str(raised)
