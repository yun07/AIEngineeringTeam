"""Live-mode configuration validation before any client or request exists."""

from __future__ import annotations

import pytest

from aiteam.config import (
    ConfigError,
    FAKE_CONFIG_PATH,
    load_config,
    validate_live_config,
)

LIMITS = """
[limits]
max_tasks_per_plan = 3
max_turns_per_session = 12
max_llm_calls_per_task = 20
max_attempts = 2
command_timeout_seconds = 120
max_tool_output_chars = 8000
"""


def _toml(
    *,
    provider: str = "openai",
    orchestrator: str = "gpt-4.1",
    developer: str = "gpt-4.1-mini",
    qa: str = "gpt-4.1-mini",
    timeout: str = "60",
    pricing: bool = True,
    max_context: bool = True,
) -> str:
    parts = [
        "[provider]",
        f'name = "{provider}"',
        f"timeout_seconds = {timeout}",
        "",
        "[models]",
        f'orchestrator = "{orchestrator}"',
        f'developer = "{developer}"',
        f'qa = "{qa}"',
        LIMITS,
        "[cost]",
        "max_output_tokens_per_call = 1200",
        "safety_margin_percent = 10",
        'estimator = "tiktoken"',
    ]
    if max_context:
        parts.append("max_context_tokens = 100000")
    if pricing:
        for model in dict.fromkeys((orchestrator, developer, qa)):
            parts.extend(
                [
                    f'[pricing."{model}"]',
                    "input_per_mtok = 0.4",
                    "output_per_mtok = 1.6",
                ]
            )
    return "\n".join(parts) + "\n"


def _write(tmp_path, **overrides):
    path = tmp_path / "aiteam.toml"
    path.write_text(_toml(**overrides), encoding="utf-8")
    return path


def test_valid_live_config_passes(tmp_path):
    config = load_config(_write(tmp_path))

    validate_live_config(config)

    assert config.provider.timeout_seconds == 60
    assert config.models.for_role("qa") == "gpt-4.1-mini"


def test_fake_mode_is_skipped_by_live_validation():
    config = load_config(FAKE_CONFIG_PATH)

    validate_live_config(config)


def test_provider_other_than_openai_is_refused(tmp_path):
    config = load_config(_write(tmp_path, provider="anthropic"))

    with pytest.raises(ConfigError, match="live provider must be 'openai'"):
        validate_live_config(config)


def test_unsupported_model_is_refused_even_with_pricing(tmp_path):
    config = load_config(
        _write(
            tmp_path,
            orchestrator="gpt-3.5-turbo",
            pricing=True,
        )
    )

    with pytest.raises(ConfigError, match="allowlist"):
        validate_live_config(config)


def test_missing_pricing_is_refused(tmp_path):
    config = load_config(_write(tmp_path, pricing=False))

    with pytest.raises(ConfigError, match="pricing for model"):
        validate_live_config(config)


def test_placeholder_model_is_refused(tmp_path):
    config = load_config(_write(tmp_path, orchestrator="update-me"))

    with pytest.raises(ConfigError, match="placeholder"):
        validate_live_config(config)


def test_negative_price_is_refused_at_load(tmp_path):
    path = _write(tmp_path)
    path.write_text(
        _toml().replace("input_per_mtok = 0.4", "input_per_mtok = -1"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must not be negative"):
        load_config(path)


def test_non_numeric_price_is_refused_at_load(tmp_path):
    path = _write(tmp_path)
    path.write_text(
        _toml().replace('input_per_mtok = 0.4', 'input_per_mtok = "free"'),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must be a number"):
        load_config(path)


@pytest.mark.parametrize("timeout", ["0", "-5", "true"])
def test_timeout_must_be_a_positive_integer(tmp_path, timeout):
    with pytest.raises(ConfigError, match="timeout_seconds"):
        load_config(_write(tmp_path, timeout=timeout))


def test_timeout_is_parsed(tmp_path):
    config = load_config(_write(tmp_path, timeout="30"))

    assert config.provider.timeout_seconds == 30


def test_live_config_without_context_window_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="max_context_tokens is required"):
        load_config(_write(tmp_path, max_context=False))


def _replace_price(path, old: str, new: str, count: int = -1):
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old, new, count), encoding="utf-8")
    return path


def test_zero_input_price_is_refused_in_live_mode(tmp_path):
    # A parsed zero price must not survive live validation: it would record
    # real spend as 0 USD.
    path = _replace_price(_write(tmp_path), "input_per_mtok = 0.4", "input_per_mtok = 0", 1)
    config = load_config(path)

    with pytest.raises(
        ConfigError,
        match=r"pricing\.gpt-4\.1\.input_per_mtok must be greater than 0",
    ):
        validate_live_config(config)


def test_zero_float_output_price_is_refused_in_live_mode(tmp_path):
    path = _replace_price(
        _write(tmp_path), "output_per_mtok = 1.6", "output_per_mtok = 0.0", 1
    )
    config = load_config(path)

    with pytest.raises(
        ConfigError,
        match=r"pricing\.gpt-4\.1\.output_per_mtok must be greater than 0",
    ):
        validate_live_config(config)


def test_zero_price_names_the_offending_model(tmp_path):
    # Only the gpt-4.1-mini block is zeroed; the message must name that model
    # and not the first model whose prices are valid.
    path = _write(tmp_path)
    text = path.read_text(encoding="utf-8")
    index = text.index('[pricing."gpt-4.1-mini"]')
    head, tail = text[:index], text[index:]
    path.write_text(
        head + tail.replace("output_per_mtok = 1.6", "output_per_mtok = 0", 1),
        encoding="utf-8",
    )
    config = load_config(path)

    with pytest.raises(ConfigError) as excinfo:
        validate_live_config(config)

    message = str(excinfo.value)
    assert "pricing.gpt-4.1-mini.output_per_mtok" in message
    assert "pricing.gpt-4.1.output_per_mtok" not in message


@pytest.mark.parametrize("model", ["gpt-4.1", "gpt-4.1-mini"])
def test_zero_price_is_refused_for_each_configured_model(tmp_path, model):
    path = _write(tmp_path)
    text = path.read_text(encoding="utf-8")
    index = text.index(f'[pricing."{model}"]')
    head, tail = text[:index], text[index:]
    tail = tail.replace("input_per_mtok = 0.4", "input_per_mtok = 0", 1)
    tail = tail.replace("output_per_mtok = 1.6", "output_per_mtok = 0", 1)
    path.write_text(head + tail, encoding="utf-8")
    config = load_config(path)

    with pytest.raises(ConfigError) as excinfo:
        validate_live_config(config)

    assert f"pricing.{model}.input_per_mtok" in str(excinfo.value)


def test_fake_mode_is_not_forced_to_configure_prices():
    config = load_config(FAKE_CONFIG_PATH)

    assert config.pricing, "the fake fixture still declares zero prices"
    assert all(
        entry["input_per_mtok"] == 0.0 and entry["output_per_mtok"] == 0.0
        for entry in config.pricing.values()
    )

    # Zero prices pass because live validation is skipped entirely for fake.
    validate_live_config(config)
