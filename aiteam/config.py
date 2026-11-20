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


@dataclass(frozen=True)
class Config:
    provider: ProviderSettings
    models: RoleModels
    limits: Limits
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

    return Config(
        provider=ProviderSettings(name=provider_name.strip()),
        models=RoleModels(**model_values),
        limits=limits,
        pricing=pricing,
        source=config_path,
    )


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
