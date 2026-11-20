"""Credential resolution and exact-value redaction.

Only the trusted engine calls into this module. A resolved key is held in
memory long enough to build the provider client and to create a
:class:`SecretBoundary`; it is never written to state, transcripts, prompts,
events or child environments.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_VAR = "OPENAI_API_KEY"
REDACTED = "[REDACTED]"


class SecretError(ValueError):
    """Raised when a required secret is missing or unsafe to read."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _dotenv_path(path: Path, root: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=False)
    root_resolved = root.resolve(strict=False)

    # Refuse any path whose real target escapes the repository. This covers a
    # ``.env`` symlink that points outside the checkout.
    if not _is_within(resolved, root_resolved):
        raise SecretError(
            "refusing to read a .env file outside the repository"
        )
    return resolved


def _parse_dotenv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[name] = value
    return values


def _read_dotenv(path: Path, root: Path) -> dict[str, str]:
    safe_path = _dotenv_path(path, root)
    if not safe_path.is_file():
        return {}
    return _parse_dotenv(safe_path.read_text(encoding="utf-8"))


def resolve_api_key(
    *,
    env_var: str = DEFAULT_ENV_VAR,
    environ: Mapping[str, str] | None = None,
    dotenv_path: str | Path | None = None,
    root: str | Path | None = None,
) -> str:
    """Return the configured key from the environment or a local ``.env``.

    The environment always wins. The ``.env`` fallback is for local
    development only; a path outside the repository, including through a
    symlink, is refused.
    """
    source = os.environ if environ is None else environ
    value = source.get(env_var, "").strip()
    if value:
        return value

    repo_root = REPO_ROOT if root is None else Path(root)
    path = Path(".env") if dotenv_path is None else Path(dotenv_path)
    values = _read_dotenv(path, repo_root)
    value = values.get(env_var, "").strip()
    if value:
        return value

    raise SecretError(
        f"{env_var} is not set; live mode refuses to start without a key"
    )


class SecretBoundary:
    """Redact and detect exact known secret values.

    ``repr()`` deliberately exposes only the number of values, never a value
    itself.
    """

    __slots__ = ("_values",)

    def __init__(self, values: object) -> None:
        if isinstance(values, str):
            candidates = (values,)
        else:
            candidates = tuple(values)  # type: ignore[arg-type]
        cleaned = {
            value.strip()
            for value in candidates
            if isinstance(value, str) and value.strip()
        }
        if not cleaned:
            raise ValueError("SecretBoundary requires at least one non-empty value")
        # Longest first so a longer secret is redacted before a shorter one
        # that happens to be a substring of it.
        self._values = tuple(sorted(cleaned, key=len, reverse=True))

    @property
    def values(self) -> tuple[str, ...]:
        return self._values

    def redact(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text
        redacted = text
        for value in self._values:
            if value in redacted:
                redacted = redacted.replace(value, REDACTED)
        return redacted

    def sanitize(self, text: str) -> str:
        """Alias used by call sites that describe the action, not the value."""
        return self.redact(text)

    def contains_any(self, text: str) -> bool:
        if not isinstance(text, str) or not text:
            return False
        return any(value in text for value in self._values)

    def __bool__(self) -> bool:
        return bool(self._values)

    def __repr__(self) -> str:
        return f"SecretBoundary(values={len(self._values)})"
