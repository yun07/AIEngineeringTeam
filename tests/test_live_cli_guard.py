"""CLI guards: live mode validates before key lookup or client creation."""

from __future__ import annotations

from aiteam import cli
from aiteam.config import FAKE_CONFIG_PATH
from aiteam.providers.openai_provider import ProviderError
from aiteam.secrets import SecretError

DUMMY_KEY = "sk-dummy-cli-redaction-key"

LIMITS = """
[limits]
max_tasks_per_plan = 3
max_turns_per_session = 12
max_llm_calls_per_task = 20
max_attempts = 2
command_timeout_seconds = 120
max_tool_output_chars = 8000
"""


def _write_live_config(tmp_path, *, pricing: bool = True, model: str = "gpt-4.1-mini"):
    pricing_block = ""
    if pricing:
        pricing_block = f"""
[pricing."{model}"]
input_per_mtok = 0.4
output_per_mtok = 1.6
"""
    text = f"""
[provider]
name = "openai"
timeout_seconds = 60

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
{pricing_block}
"""
    path = tmp_path / "live.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _live_args(config_path, root, *, budget=True):
    args = [
        "run",
        "--project",
        "demo",
        "--request",
        "Create a demo notes file",
        "--config",
        str(config_path),
        "--root",
        str(root),
    ]
    if budget:
        args.extend(["--budget", "0.01"])
    return args


def test_live_mode_requires_budget_before_key_lookup(tmp_path, monkeypatch, capsys):
    path = _write_live_config(tmp_path)
    called = {"resolve": False, "factory": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("key lookup must not happen without a budget")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("client must not be created without a budget")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(path, tmp_path, budget=False))

    assert code == 2
    assert called == {"resolve": False, "factory": False}
    assert "requires --budget" in capsys.readouterr().err


def test_live_mode_missing_key_exits_without_creating_a_client(
    tmp_path, monkeypatch, capsys
):
    path = _write_live_config(tmp_path)
    called = {"factory": False}

    def missing_key():
        raise SecretError("OPENAI_API_KEY is not set; live mode refuses to start")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("client must not be created without a key")

    monkeypatch.setattr(cli, "resolve_api_key", missing_key)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(path, tmp_path))

    captured = capsys.readouterr()
    assert code == 2
    assert called["factory"] is False
    assert "OPENAI_API_KEY is not set" in captured.err
    assert "[REDACTED]" not in captured.err


def test_live_mode_missing_pricing_exits_before_key_lookup(
    tmp_path, monkeypatch, capsys
):
    path = _write_live_config(tmp_path, pricing=False)
    called = {"resolve": False, "factory": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("pricing must be validated before key lookup")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("client must not be created with invalid pricing")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(path, tmp_path))

    assert code == 2
    assert called == {"resolve": False, "factory": False}
    assert "pricing" in capsys.readouterr().err


def test_live_mode_zero_price_exits_before_key_lookup(
    tmp_path, monkeypatch, capsys
):
    path = _write_live_config(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "input_per_mtok = 0.4", "input_per_mtok = 0", 1
        ),
        encoding="utf-8",
    )
    called = {"resolve": False, "factory": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("a zero price must be rejected before key lookup")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("a zero price must be rejected before a client")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(path, tmp_path))

    assert code == 2
    assert called == {"resolve": False, "factory": False}
    assert "greater than 0" in capsys.readouterr().err


def test_live_mode_unsupported_model_exits_before_key_lookup(
    tmp_path, monkeypatch, capsys
):
    path = _write_live_config(tmp_path, model="gpt-3.5-turbo")
    called = {"resolve": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("model validation must precede key lookup")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)

    code = cli.main(_live_args(path, tmp_path))

    assert code == 2
    assert called["resolve"] is False
    assert "allowlist" in capsys.readouterr().err


def test_provider_setup_error_is_redacted_in_cli_output(
    tmp_path, monkeypatch, capsys
):
    path = _write_live_config(tmp_path)

    monkeypatch.setattr(cli, "resolve_api_key", lambda: DUMMY_KEY)

    def fail_factory(*args, **kwargs):
        raise ProviderError("api_error", f"provider rejected {DUMMY_KEY}")

    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(path, tmp_path))

    captured = capsys.readouterr()
    assert code == 2
    assert DUMMY_KEY not in captured.err
    assert "[REDACTED]" in captured.err


def test_live_mode_rejects_fake_config_without_the_fake_flag(
    tmp_path, monkeypatch, capsys
):
    called = {"resolve": False, "factory": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("fake config must be rejected before key lookup")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("fake config must be rejected before client creation")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(_live_args(FAKE_CONFIG_PATH, tmp_path))

    assert code == 2
    assert called == {"resolve": False, "factory": False}
    assert "requires --fake" in capsys.readouterr().err


def test_fake_mode_never_resolves_a_key_or_builds_a_live_provider(
    tmp_path, monkeypatch
):
    called = {"resolve": False, "factory": False}

    def fail_resolve():
        called["resolve"] = True
        raise AssertionError("fake mode must not resolve a key")

    def fail_factory(*args, **kwargs):
        called["factory"] = True
        raise AssertionError("fake mode must not build a live provider")

    monkeypatch.setattr(cli, "resolve_api_key", fail_resolve)
    monkeypatch.setattr(cli, "create_openai_provider", fail_factory)

    code = cli.main(
        [
            "run",
            "--fake",
            "--project",
            "demo",
            "--request",
            "Create a demo notes file",
            "--root",
            str(tmp_path),
            "--plan-only",
        ]
    )

    assert code == 1
    assert called == {"resolve": False, "factory": False}
