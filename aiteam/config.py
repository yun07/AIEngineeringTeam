"""Configuration loading and validation.

Only models, prices and limits are configurable. Command policy stays in code
as constants in the policy module. Environment overrides and secret redaction
arrive with the milestones that need them: M3 for pricing validation and M5
for the live provider.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "aiteam.toml"
FAKE_CONFIG_PATH = REPO_ROOT / "tests" / "fixtures" / "aiteam.fake.toml"

ROLE_NAMES = ("orchestrator", "developer", "qa")
# Live provider names the engine knows how to validate. Anything else fails
# closed rather than falling through to a permissive default.
LIVE_PROVIDER_NAMES: tuple[str, ...] = ("openai", "deepseek")
COST_KEYS = (
    "max_output_tokens_per_call",
    "safety_margin_percent",
    "max_context_tokens",
    "estimator",
)
LIMIT_KEYS = (
    "max_tasks_per_plan",
    "max_turns_per_session",
    "max_llm_calls_per_task",
    "max_attempts",
    "command_timeout_seconds",
    "max_tool_output_chars",
)


class ConfigError(ValueError):
    """Raised when the configuration file is missing or invalid."""


@dataclass(frozen=True)
class Limits:
    max_tasks_per_plan: int = 3
    max_turns_per_session: int = 12
    max_llm_calls_per_task: int = 20
    max_attempts: int = 2
    command_timeout_seconds: int = 120
    max_tool_output_chars: int = 8000


@dataclass(frozen=True)
class CostSettings:
    max_output_tokens_per_call: int = 1200
    safety_margin_percent: float = 10.0
    max_context_tokens: int | None = None
    estimator: str = "tiktoken"


@dataclass(frozen=True)
class RoleModels:
    orchestrator: str
    developer: str
    qa: str

    def for_role(self, role: str) -> str:
        if role not in ROLE_NAMES:
            raise ConfigError(f"unknown role {role!r}")
        return getattr(self, role)


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    timeout_seconds: int = 60
    # OpenAI-compatible endpoints (for example DeepSeek) need an explicit base
    # URL. ``None`` keeps the SDK default endpoint, so OpenAI is unchanged.
    base_url: str | None = None


@dataclass(frozen=True)
class Config:
    provider: ProviderSettings
    models: RoleModels
    limits: Limits
    cost: CostSettings = field(default_factory=CostSettings)
    pricing: dict[str, dict[str, float]] = field(default_factory=dict)
    source: Path | None = None


def load_config(path: str | Path) -> Config:
    """Load and validate a TOML configuration file."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"configuration file not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    provider_raw = raw.get("provider")
    if not isinstance(provider_raw, dict):
        raise ConfigError("missing [provider] section")
    provider_name = provider_raw.get("name")
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ConfigError("provider.name must be a non-empty string")

    models_raw = raw.get("models")
    if not isinstance(models_raw, dict):
        raise ConfigError("missing [models] section")
    model_values: dict[str, str] = {}
    for role in ROLE_NAMES:
        value = models_raw.get(role)
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"models.{role} must be a non-empty string")
        model_values[role] = value.strip()

    limits = _parse_limits(raw.get("limits"))
    pricing = _parse_pricing(raw.get("pricing"))
    cost = _parse_cost(raw.get("cost"), provider_name=provider_name.strip())
    timeout_seconds = _parse_provider_timeout(provider_raw.get("timeout_seconds", 60))
    base_url = _parse_provider_base_url(provider_raw.get("base_url"))

    return Config(
        provider=ProviderSettings(
            name=provider_name.strip(),
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        ),
        models=RoleModels(**model_values),
        limits=limits,
        cost=cost,
        pricing=pricing,
        source=config_path,
    )


def _parse_provider_base_url(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError("provider.base_url must be a non-empty string when set")
    return raw.strip()


def _parse_provider_timeout(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ConfigError("provider.timeout_seconds must be an integer")
    if raw < 1:
        raise ConfigError("provider.timeout_seconds must be at least 1")
    return raw


def _parse_limits(raw: Any) -> Limits:
    if not isinstance(raw, dict):
        raise ConfigError("missing [limits] section")
    unknown = sorted(set(raw) - set(LIMIT_KEYS))
    if unknown:
        raise ConfigError(f"unknown [limits] keys: {', '.join(unknown)}")
    values: dict[str, int] = {}
    for key in LIMIT_KEYS:
        if key not in raw:
            raise ConfigError(f"limits.{key} is required")
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"limits.{key} must be an integer")
        if value < 1:
            raise ConfigError(f"limits.{key} must be at least 1")
        values[key] = value
    return Limits(**values)


def _parse_pricing(raw: Any) -> dict[str, dict[str, float]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("[pricing] must be a table of per-model entries")
    pricing: dict[str, dict[str, float]] = {}
    for model, entry in raw.items():
        if not isinstance(entry, dict):
            raise ConfigError(f"pricing.{model} must be a table")
        parsed: dict[str, float] = {}
        for key in ("input_per_mtok", "output_per_mtok"):
            if key not in entry:
                raise ConfigError(f"pricing.{model}.{key} is required")
            value = entry[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(f"pricing.{model}.{key} must be a number")
            if value < 0:
                raise ConfigError(f"pricing.{model}.{key} must not be negative")
            parsed[key] = float(value)
        pricing[str(model)] = parsed
    return pricing


def _parse_cost(raw: Any, *, provider_name: str) -> CostSettings:
    if raw is None:
        if provider_name == "fake":
            return CostSettings()
        raise ConfigError(
            "missing [cost] section; live mode requires max_context_tokens and "
            "an explicit estimator"
        )
    if not isinstance(raw, dict):
        raise ConfigError("[cost] must be a table")
    unknown = sorted(set(raw) - set(COST_KEYS))
    if unknown:
        raise ConfigError(f"unknown [cost] keys: {', '.join(unknown)}")

    estimator = raw.get("estimator", "tiktoken")
    if estimator != "tiktoken":
        raise ConfigError("cost.estimator must be 'tiktoken'")
    max_output = raw.get("max_output_tokens_per_call", 1200)
    if isinstance(max_output, bool) or not isinstance(max_output, int):
        raise ConfigError("cost.max_output_tokens_per_call must be an integer")
    if max_output < 1:
        raise ConfigError("cost.max_output_tokens_per_call must be at least 1")
    margin = raw.get("safety_margin_percent", 10.0)
    if isinstance(margin, bool) or not isinstance(margin, (int, float)):
        raise ConfigError("cost.safety_margin_percent must be a number")
    if margin < 0:
        raise ConfigError("cost.safety_margin_percent must not be negative")
    max_context = raw.get("max_context_tokens")
    if max_context is not None:
        if isinstance(max_context, bool) or not isinstance(max_context, int):
            raise ConfigError("cost.max_context_tokens must be an integer")
        if max_context < 1:
            raise ConfigError("cost.max_context_tokens must be at least 1")
    if provider_name != "fake" and max_context is None:
        raise ConfigError(
            "cost.max_context_tokens is required in live mode; no default is applied"
        )
    return CostSettings(
        max_output_tokens_per_call=max_output,
        safety_margin_percent=float(margin),
        max_context_tokens=max_context,
        estimator=estimator,
    )


_PLACEHOLDER_TOKENS = (
    "update-me",
    "changeme",
    "todo",
    "your-model-id",
    "xxx",
)


def validate_live_config(config: Config) -> None:
    """Validate everything that must hold before a live client is created.

    This is deliberately separate from :func:`load_config`: fake mode uses
    simple fixture files, while live mode must reject unknown models, missing
    pricing and placeholder identifiers before any request is made.
    """
    if config.provider.name == "fake":
        return
    if config.provider.name not in LIVE_PROVIDER_NAMES:
        raise ConfigError(
            f"live provider must be one of {LIVE_PROVIDER_NAMES}, "
            f"got {config.provider.name!r}"
        )
    if config.provider.name == "deepseek" and not (
        isinstance(config.provider.base_url, str)
        and config.provider.base_url.strip()
    ):
        raise ConfigError(
            "provider.base_url is required for provider 'deepseek'; the engine "
            "will not guess an endpoint"
        )
    if (
        isinstance(config.provider.timeout_seconds, bool)
        or not isinstance(config.provider.timeout_seconds, int)
        or config.provider.timeout_seconds < 1
    ):
        raise ConfigError("provider.timeout_seconds must be a positive integer")

    # Imported lazily so config parsing stays independent of the cost package
    # at import time. The allowlist has a single source of truth.
    from aiteam.cost.tokens import SUPPORTED_MODELS

    for role in ROLE_NAMES:
        model = config.models.for_role(role)
        lowered = model.casefold()
        if any(token in lowered for token in _PLACEHOLDER_TOKENS) or (
            "<" in model and ">" in model
        ):
            raise ConfigError(
                f"models.{role} = {model!r} looks like a placeholder; "
                "set a real model identifier"
            )
        if model not in SUPPORTED_MODELS:
            raise ConfigError(
                f"models.{role} = {model!r} is not in the supported model "
                f"allowlist {sorted(SUPPORTED_MODELS)}"
            )

        entry = config.pricing.get(model)
        if not isinstance(entry, dict):
            raise ConfigError(
                f"pricing for model {model!r} is required in live mode"
            )
        for key in ("input_per_mtok", "output_per_mtok"):
            value = entry.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(
                    f"pricing.{model}.{key} must be a positive number in live "
                    "mode; got a non-numeric value"
                )
            # A zero price would record real spend as 0 USD, so live mode
            # rejects it. Fake mode never reaches this check and keeps its
            # zero-price fixture.
            if value <= 0:
                raise ConfigError(
                    f"pricing.{model}.{key} must be greater than 0 in live "
                    f"mode; got {value!r}. A zero price would record real "
                    "cost as 0 USD"
                )

    if config.cost.max_context_tokens is None:
        raise ConfigError(
            "cost.max_context_tokens is required in live mode; no default is applied"
        )
