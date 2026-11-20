"""Config rules for cost settings, especially the live-only context window."""

from __future__ import annotations

import pytest

from aiteam.config import ConfigError, load_config

BASE_TEMPLATE = """
[provider]
name = "{provider}"

[models]
orchestrator = "gpt-4.1"
developer = "gpt-4.1-mini"
qa = "gpt-4.1-mini"

[limits]
max_tasks_per_plan = 3
max_turns_per_session = 12
max_llm_calls_per_task = 20
max_attempts = 2
command_timeout_seconds = 120
max_tool_output_chars = 8000
"""


def write_config(tmp_path, *, provider: str, cost_block: str = ""):
    path = tmp_path / "aiteam.toml"
    path.write_text(
        BASE_TEMPLATE.format(provider=provider) + cost_block, encoding="utf-8"
    )
    return path


def test_live_mode_refuses_missing_cost_section(tmp_path):
    path = write_config(tmp_path, provider="openai")

    with pytest.raises(ConfigError, match=r"missing \[cost\] section"):
        load_config(path)


def test_live_mode_refuses_missing_max_context_tokens(tmp_path):
    path = write_config(
        tmp_path,
        provider="openai",
        cost_block="""
[cost]
max_output_tokens_per_call = 1200
safety_margin_percent = 10
estimator = "tiktoken"
""",
    )

    with pytest.raises(ConfigError, match="max_context_tokens is required"):
        load_config(path)


def test_live_mode_accepts_an_explicit_max_context_tokens(tmp_path):
    path = write_config(
        tmp_path,
        provider="openai",
        cost_block="""
[cost]
max_output_tokens_per_call = 900
safety_margin_percent = 5
max_context_tokens = 100000
estimator = "tiktoken"
""",
    )

    config = load_config(path)

    assert config.cost.max_context_tokens == 100000
    assert config.cost.max_output_tokens_per_call == 900
    assert config.cost.safety_margin_percent == pytest.approx(5.0)


def test_fake_mode_does_not_need_cost_settings(tmp_path):
    path = write_config(tmp_path, provider="fake")

    config = load_config(path)

    assert config.cost.max_context_tokens is None
    assert config.cost.max_output_tokens_per_call == 1200
    assert config.cost.safety_margin_percent == pytest.approx(10.0)


def test_fake_mode_also_accepts_an_explicit_expensive_limit(tmp_path):
    path = write_config(
        tmp_path,
        provider="fake",
        cost_block="""
[cost]
max_output_tokens_per_call = 100
max_context_tokens = 5000
""",
    )

    config = load_config(path)

    assert config.cost.max_context_tokens == 5000
    assert config.cost.max_output_tokens_per_call == 100
