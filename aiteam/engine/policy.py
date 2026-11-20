"""Application-level command policy and human approval gate.

This is a guardrail layer, not an OS sandbox. It decides which commands may
run, builds the scrubbed child environment, and asks the human before any
command that would execute generated code.

Rules, in order:

1. DENY wins. A denied command never produces an approval prompt.
2. CONFIRM asks the human for that one execution: ``y`` or ``n``, default No.
3. AUTO covers a tiny exact-argv informational allowlist only.
4. Non-interactive input denies every CONFIRM command.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Sequence

CHILD_ENV_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "PATHEXT",
    "SystemRoot",
    "WINDIR",
    "TEMP",
    "TMP",
    "COMSPEC",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
)

SECRET_NAME_PREFIXES: tuple[str, ...] = (
    "AITEAM_",
    "OPENAI_",
    "AZURE_",
    "AWS_",
    "ANTHROPIC_",
    "GITHUB_",
)
SECRET_NAME_FRAGMENTS: tuple[str, ...] = ("TOKEN", "SECRET", "KEY", "PASSWORD")

SHELL_WRAPPERS: frozenset[str] = frozenset(
    {
        "cmd",
        "powershell",
        "pwsh",
        "sh",
        "bash",
        "zsh",
        "wsl",
        "cscript",
        "wscript",
        "mshta",
        "rundll32",
        "start",
    }
)

INSTALL_EXECUTABLES: frozenset[str] = frozenset(
    {
        "pip",
        "pip3",
        "conda",
        "mamba",
        "npm",
        "npx",
        "yarn",
        "pnpm",
        "winget",
        "choco",
        "scoop",
        "apt",
        "apt-get",
        "brew",
        "poetry",
        "pipenv",
        "uv",
    }
)

# Exact argument vectors allowed without approval. Prefix matching is never
# used: ``python`` alone must never become a general execution grant.
INFORMATIONAL_ALLOWLIST: tuple[tuple[str, ...], ...] = (
    ("python", "--version"),
    ("git", "status", "--short"),
)

# The single test command QA may request. It is CONFIRM, never AUTO.
TEST_ALLOWLIST: tuple[tuple[str, ...], ...] = (
    ("python", "-m", "pytest", "qa_tests", "-q"),
)


class Risk(str, Enum):
    AUTO = "auto"
    CONFIRM = "confirm"
    DENY = "deny"


class ApprovalOutcome(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class CommandDecision:
    risk: Risk
    reason: str


def _executable_key(token: str) -> str:
    name = Path(token).name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def _normalized(argv: Sequence[str]) -> tuple[str, ...]:
    if not argv:
        return ()
    return (_executable_key(str(argv[0])),) + tuple(
        str(part).lower() for part in argv[1:]
    )


def classify_command(argv: Sequence[str]) -> CommandDecision:
    """Classify a command. Unknown commands are denied by default."""
    if not isinstance(argv, (list, tuple)) or not argv:
        return CommandDecision(Risk.DENY, "empty command")
    if not all(isinstance(part, str) and part for part in argv):
        return CommandDecision(Risk.DENY, "arguments must be non-empty strings")

    normalized = _normalized(argv)
    executable, arguments = normalized[0], normalized[1:]

    if executable in SHELL_WRAPPERS:
        return CommandDecision(
            Risk.DENY, f"shell wrapper {executable!r} is not permitted"
        )
    if executable in INSTALL_EXECUTABLES:
        return CommandDecision(
            Risk.DENY, f"package installation via {executable!r} is denied"
        )
    if any(part.lower() in INSTALL_EXECUTABLES for part in arguments):
        return CommandDecision(
            Risk.DENY, "package installation inside a wrapped command is denied"
        )
    if any(".env" in part for part in arguments + (argv[0],)):
        return CommandDecision(Risk.DENY, "access to secret-like paths is denied")

    if executable.startswith("python"):
        if "-c" in arguments:
            return CommandDecision(
                Risk.DENY, "inline code execution with -c is denied"
            )
        if arguments[:2] == ("-m", "pip"):
            return CommandDecision(Risk.DENY, "package installation is denied")
        if arguments[:2] == ("-m", "pytest"):
            if normalized in TEST_ALLOWLIST:
                return CommandDecision(
                    Risk.CONFIRM,
                    "runs the project test suite and executes generated code",
                )
            return CommandDecision(
                Risk.DENY,
                "only the exact test command 'python -m pytest qa_tests -q' is allowed",
            )

    if normalized in INFORMATIONAL_ALLOWLIST:
        return CommandDecision(Risk.AUTO, "informational command on the allowlist")

    return CommandDecision(
        Risk.DENY, f"command {argv[0]!r} is not on the exact-argv allowlist"
    )


def build_child_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build a scrubbed environment from an allowlist only."""
    origin = os.environ if source is None else source
    child: dict[str, str] = {}
    for name in CHILD_ENV_ALLOWLIST:
        value = origin.get(name)
        if value:
            child[name] = value
    child["PYTHONUTF8"] = "1"
    child["PYTHONIOENCODING"] = "utf-8"

    for name in list(child):
        upper = name.upper()
        if upper.startswith(SECRET_NAME_PREFIXES):
            child.pop(name, None)
        elif any(fragment in upper for fragment in SECRET_NAME_FRAGMENTS):
            child.pop(name, None)
    return child


def format_approval_prompt(
    *,
    argv: Sequence[str],
    cwd: str,
    purpose: str,
    target_files: Sequence[str] = (),
) -> str:
    files = "\n".join(f"  - {item}" for item in target_files) or "  (none declared)"
    return (
        "The AI engineering team wants to run a command that executes "
        "unreviewed AI-generated code.\n"
        "\n"
        f"Command: {' '.join(argv)}\n"
        f"Working directory: {cwd}\n"
        f"Purpose: {purpose}\n"
        "Files that will be executed:\n"
        f"{files}\n"
        "\n"
        "This grants exactly one execution. There is no session-wide approval.\n"
        "Approve this execution? [y/N]: "
    )


@dataclass
class ApprovalGate:
    """Human approval gate owned by the engine, never by an agent."""

    approver: Callable[[str], bool] | None = None
    interactive: bool = False
    requested: list[dict[str, object]] = field(default_factory=list)

    def request(
        self,
        *,
        argv: Sequence[str],
        cwd: str,
        purpose: str,
        target_files: Sequence[str] = (),
    ) -> tuple[ApprovalOutcome, str | None]:
        self.requested.append({"argv": list(argv), "cwd": cwd})
        if not self.interactive or self.approver is None:
            return ApprovalOutcome.DENIED, "non_interactive_denied"

        prompt = format_approval_prompt(
            argv=argv, cwd=cwd, purpose=purpose, target_files=target_files
        )
        try:
            approved = bool(self.approver(prompt))
        except EOFError:
            return ApprovalOutcome.DENIED, "approval_input_unavailable"
        if approved:
            return ApprovalOutcome.APPROVED, None
        return ApprovalOutcome.DENIED, "user_denied"
