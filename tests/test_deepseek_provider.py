"""DeepSeek support through the OpenAI-compatible adapter.

No test here performs a network call: the SDK client is replaced by a recorder
or by ``FakeClient``, and every API-key value is a dummy string.
"""

from __future__ import annotations

import json
from dataclasses import replace

import openai
import pytest

from aiteam import cli
from aiteam.config import (
    ConfigError,
    ProviderSettings,
    RoleModels,
    load_config,
    validate_live_config,
)
from aiteam.cost import tokens
from aiteam.cost.tokens import TokenEstimationError
from aiteam.providers import openai_provider as adapter
from aiteam.providers.base import ChatMessage, LLMResponse, ToolSpec, Usage
from aiteam.providers.openai_provider import (
    OpenAIProvider,
    create_openai_client,
    create_openai_provider,
)
from aiteam.secrets import (
    SecretBoundary,
    SecretError,
    api_key_env_var,
    resolve_api_key,
)
from aiteam.state.store import StateStore
from tests.fakes import StubProvider, make_billing_config, plan_payload
from tests.test_openai_provider import FakeClient, _response

DUMMY_KEY = "sk-dummy-deepseek-not-a-real-key"
BASE_URL = "https://api.example.invalid/v1"
MODEL = "deepseek-flash"

LIMITS = """
[limits]
max_tasks_per_plan = 3
max_turns_per_session = 12
max_llm_calls_per_task = 20
max_attempts = 2
command_timeout_seconds = 120
max_tool_output_chars = 8000
"""


def _adapter(provider_name: str = "openai", response=None):
    client = FakeClient(response if response is not None else _response(text="done"))
    provider = OpenAIProvider(
        client,
        secret_boundary=SecretBoundary([DUMMY_KEY]),
        provider_name=provider_name,
    )
    return provider, client


def _billing_config(provider_name: str = "deepseek", base_url: str | None = BASE_URL):
    return replace(
        make_billing_config(),
        provider=ProviderSettings(
            name=provider_name, timeout_seconds=60, base_url=base_url
        ),
        models=RoleModels(
            orchestrator=MODEL, developer=MODEL, qa=MODEL
        ),
        pricing={MODEL: {"input_per_mtok": 0.4, "output_per_mtok": 1.6}},
    )


def _toml(
    *,
    provider: str = "deepseek",
    base_url: str | None = BASE_URL,
    model: str = MODEL,
) -> str:
    base_line = "" if base_url is None else f'base_url = "{base_url}"\n'
    return f"""
[provider]
name = "{provider}"
timeout_seconds = 60
{base_line}
[models]
orchestrator = "{model}"
developer = "{model}"
qa = "{model}"
{LIMITS}
[cost]
max_output_tokens_per_call = 1200
safety_margin_percent = 10
max_context_tokens = 100000
estimator = "tiktoken"

[pricing."{model}"]
input_per_mtok = 0.4
output_per_mtok = 1.6
"""


def _write_config(tmp_path, **overrides):
    path = tmp_path / "aiteam.toml"
    path.write_text(_toml(**overrides), encoding="utf-8")
    return path


# --- A. base_url plumbing ---------------------------------------------------


def test_openai_client_keeps_the_sdk_default_endpoint(monkeypatch):
    captured: dict = {}

    class Recorder:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(openai, "OpenAI", Recorder)

    client = create_openai_client(api_key=DUMMY_KEY, timeout_seconds=30)

    assert isinstance(client, Recorder)
    assert captured["api_key"] == DUMMY_KEY
    assert captured["timeout"] == 30
    assert captured.get("base_url") is None


def test_deepseek_base_url_reaches_the_sdk_client(monkeypatch):
    captured: dict = {}

    class Recorder:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(openai, "OpenAI", Recorder)

    create_openai_client(
        api_key=DUMMY_KEY, timeout_seconds=60, base_url=BASE_URL
    )

    assert captured["base_url"] == BASE_URL
    assert captured["api_key"] == DUMMY_KEY


def test_factory_passes_base_url_and_provider_name(monkeypatch):
    captured: dict = {}

    def fake_client_factory(*, api_key, timeout_seconds, base_url=None):
        captured.update(
            api_key=api_key, timeout=timeout_seconds, base_url=base_url
        )
        return FakeClient(_response(text="done"))

    monkeypatch.setattr(adapter, "create_openai_client", fake_client_factory)

    provider = create_openai_provider(
        _billing_config(), DUMMY_KEY, boundary=SecretBoundary([DUMMY_KEY])
    )

    assert captured == {"api_key": DUMMY_KEY, "timeout": 60, "base_url": BASE_URL}
    assert provider.name == "deepseek"


# --- B. request bodies ------------------------------------------------------


def test_openai_request_uses_max_completion_tokens_only():
    provider, client = _adapter("openai")

    provider.complete(
        model="gpt-4.1-mini",
        system="sys",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=64,
    )

    request = client.completions.requests[0]
    assert request["max_completion_tokens"] == 64
    assert "max_tokens" not in request
    assert "extra_body" not in request
    assert "thinking" not in request


def test_deepseek_request_uses_max_tokens_and_disables_thinking():
    provider, client = _adapter("deepseek")

    provider.complete(
        model=MODEL,
        system="sys",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        max_output_tokens=64,
    )

    request = client.completions.requests[0]
    assert request["max_tokens"] == 64
    assert "max_completion_tokens" not in request
    assert request["extra_body"] == {"thinking": {"type": "disabled"}}
    # The flag travels inside extra_body; it is not a typed SDK kwarg.
    assert "thinking" not in request


def test_deepseek_request_keeps_messages_and_tool_schema():
    spec = ToolSpec(
        name="write_file",
        description="write a file",
        parameters={"type": "object"},
    )
    provider, client = _adapter("deepseek")

    provider.complete(
        model=MODEL,
        system="sys",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[spec],
        max_output_tokens=32,
    )

    request = client.completions.requests[0]
    assert request["messages"][0] == {"role": "system", "content": "sys"}
    assert request["messages"][1] == {"role": "user", "content": "hi"}
    assert request["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "write a file",
                "parameters": {"type": "object"},
            },
        }
    ]
    # The response mapping is shared with OpenAI.
    assert provider.name == "deepseek"


def test_unsupported_provider_name_is_refused_by_the_adapter():
    with pytest.raises(ValueError, match="unsupported provider"):
        OpenAIProvider(
            FakeClient(_response()),
            secret_boundary=SecretBoundary([DUMMY_KEY]),
            provider_name="stub",
        )


# --- C. configuration validation -------------------------------------------


def test_deepseek_config_requires_base_url(tmp_path):
    config = load_config(_write_config(tmp_path, base_url=None))

    with pytest.raises(ConfigError, match="provider.base_url is required"):
        validate_live_config(config)


def test_deepseek_config_with_base_url_passes_live_validation(tmp_path):
    config = load_config(_write_config(tmp_path))

    validate_live_config(config)

    assert config.provider.name == "deepseek"
    assert config.provider.base_url == BASE_URL
    assert config.models.for_role("qa") == MODEL


def test_empty_base_url_is_refused_at_load(tmp_path):
    with pytest.raises(ConfigError, match="provider.base_url must be a non-empty"):
        load_config(_write_config(tmp_path, base_url=""))


def test_unknown_live_provider_is_refused(tmp_path):
    config = load_config(_write_config(tmp_path, provider="anthropic"))

    with pytest.raises(ConfigError, match="live provider must be one of"):
        validate_live_config(config)


# --- D. token estimation ----------------------------------------------------


def test_deepseek_flash_is_allowlisted_and_uses_cl100k():
    assert MODEL in tokens.SUPPORTED_MODELS
    assert tokens.MODEL_ENCODINGS[MODEL] == "cl100k_base"
    assert tokens.encoder_for_model(MODEL).name == "cl100k_base"
    assert tokens.estimate_text_tokens(MODEL, "hello world") > 0


def test_gpt_models_keep_their_tiktoken_encoders():
    for model in ("gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"):
        assert model in tokens.SUPPORTED_MODELS
        assert tokens.encoder_for_model(model).name == "o200k_base"


def test_unknown_model_still_fails_closed():
    with pytest.raises(TokenEstimationError, match="allowlist"):
        tokens.encoder_for_model("deepseek-chat")

    with pytest.raises(TokenEstimationError, match="allowlist"):
        tokens.encoder_for_model("gpt-3.5-turbo")


# --- E. API key selection ---------------------------------------------------


def test_provider_env_var_mapping():
    assert api_key_env_var("openai") == "OPENAI_API_KEY"
    assert api_key_env_var("deepseek") == "DEEPSEEK_API_KEY"

    with pytest.raises(SecretError, match="no API key variable"):
        api_key_env_var("anthropic")


def test_deepseek_key_is_read_from_its_own_variable(tmp_path):
    value = resolve_api_key(
        env_var="DEEPSEEK_API_KEY",
        environ={"DEEPSEEK_API_KEY": DUMMY_KEY, "OPENAI_API_KEY": "wrong-key"},
        root=tmp_path,
        dotenv_path=".env",
    )

    assert value == DUMMY_KEY


def test_openai_key_still_comes_from_openai_variable(tmp_path):
    value = resolve_api_key(
        env_var=api_key_env_var("openai"),
        environ={"OPENAI_API_KEY": DUMMY_KEY},
        root=tmp_path,
        dotenv_path=".env",
    )

    assert value == DUMMY_KEY


# --- F. CLI wiring ----------------------------------------------------------


def test_cli_uses_the_deepseek_key_variable_and_base_url(
    tmp_path, monkeypatch, capsys
):
    config_path = _write_config(tmp_path)
    root = tmp_path / "repo"
    captured: dict = {}

    def fake_resolve(*, env_var="OPENAI_API_KEY", **kwargs):
        captured["env_var"] = env_var
        return DUMMY_KEY

    def fake_factory(config, api_key, *, boundary):
        captured["provider"] = config.provider.name
        captured["base_url"] = config.provider.base_url
        captured["boundary"] = boundary
        captured["api_key"] = api_key
        return StubProvider(
            {
                "orchestrator": [
                    LLMResponse(
                        text=json.dumps(plan_payload(1)), usage=Usage(40, 20)
                    )
                ]
            }
        )

    monkeypatch.setattr(cli, "resolve_api_key", fake_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fake_factory)

    code = cli.main(
        [
            "run",
            "--project",
            "demo",
            "--request",
            "build a demo project",
            "--config",
            str(config_path),
            "--root",
            str(root),
            "--budget",
            "0.01",
            "--plan-only",
        ]
    )

    assert code == 1  # --plan-only blocks the run, which is expected
    assert captured["env_var"] == "DEEPSEEK_API_KEY"
    assert captured["provider"] == "deepseek"
    assert captured["base_url"] == BASE_URL
    assert captured["api_key"] == DUMMY_KEY
    assert captured["boundary"] is not None

    store = StateStore(root)
    usage = store.read_usage()
    assert len(usage) == 1
    assert usage[0]["model"] == MODEL
    assert usage[0]["usd"] > 0
    # The dummy key must never reach a persisted artefact.
    for path in root.rglob("*"):
        if path.is_file():
            assert DUMMY_KEY not in path.read_text(encoding="utf-8")
