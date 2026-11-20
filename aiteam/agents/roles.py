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

# Tool names that must never appear in the Developer or Orchestrator tool set.
FORBIDDEN_ROLE_TOOLS: tuple[str, ...] = ("run_command", "run_shell", "shell", "exec")


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

ROLES = {role.name: role for role in (ORCHESTRATOR, DEVELOPER)}


def get_role(name: str) -> RoleDefinition:
    try:
        return ROLES[name]
    except KeyError as exc:
        raise KeyError(f"unknown role: {name}") from exc


def model_for_role(config: Config, role: str) -> str:
    return config.models.for_role(role)
