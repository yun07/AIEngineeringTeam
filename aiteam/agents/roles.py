"""Role definitions: tool sets and prompt files.

The Developer holds read, write and list only. No shell or command tool exists
for it, and no role can grant itself another tool. QA arrives with M2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aiteam.config import Config

PROMPTS_DIR = Path(__file__).with_name("prompts")

ORCHESTRATOR_TOOLS: tuple[str, ...] = ()
DEVELOPER_TOOLS: tuple[str, ...] = ("read_file", "write_file", "list_files")
QA_TOOLS: tuple[str, ...] = (
    "read_file",
    "list_files",
    "write_file",
    "run_command",
)

# Tools that must never exist for any role: shell wrappers and interpreters.
SHELL_TOOL_NAMES: tuple[str, ...] = (
    "run_shell",
    "shell",
    "exec",
    "cmd",
    "powershell",
)

# Tool names that must never appear in the Developer or Orchestrator tool set.
# QA is the only role allowed to request command execution, and only through
# the engine's policy and approval gate.
FORBIDDEN_ROLE_TOOLS: tuple[str, ...] = ("run_command",) + SHELL_TOOL_NAMES


def forbidden_tools_for(role: RoleDefinition) -> tuple[str, ...]:
    if role.name == "qa":
        return SHELL_TOOL_NAMES
    return FORBIDDEN_ROLE_TOOLS


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    prompt_file: str
    tools: tuple[str, ...]

    def load_prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")


ORCHESTRATOR = RoleDefinition(
    name="orchestrator",
    prompt_file="orchestrator.md",
    tools=ORCHESTRATOR_TOOLS,
)
DEVELOPER = RoleDefinition(
    name="developer",
    prompt_file="developer.md",
    tools=DEVELOPER_TOOLS,
)
QA = RoleDefinition(
    name="qa",
    prompt_file="qa.md",
    tools=QA_TOOLS,
)

ROLES = {role.name: role for role in (ORCHESTRATOR, DEVELOPER, QA)}


def get_role(name: str) -> RoleDefinition:
    try:
        return ROLES[name]
    except KeyError as exc:
        raise KeyError(f"unknown role: {name}") from exc


def model_for_role(config: Config, role: str) -> str:
    return config.models.for_role(role)
