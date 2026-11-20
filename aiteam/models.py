"""Domain models for the Phase 1 workflow engine.

Only the entities the current milestone needs are defined here. UsageRecord
arrives with M3 (cost accounting) and ApprovalRecord with M2 (approvals), so
they are deliberately absent rather than declared and left unused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with a Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskState(str, Enum):
    PENDING = "pending"
    DEV_RUNNING = "dev_running"
    QA_RUNNING = "qa_running"
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    DONE = "done"


class RunState(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


TERMINAL_RUN_STATES = frozenset(
    {RunState.COMPLETED, RunState.BLOCKED, RunState.ESCALATED}
)


class Action(str, Enum):
    """Deterministic routing actions returned by next_action()."""

    ORCHESTRATE_PLAN = "orchestrate_plan"
    RUN_DEVELOPER = "run_developer"
    RUN_QA = "run_qa"
    RETRY_TASK = "retry_task"
    ESCALATE = "escalate"
    FINALIZE = "finalize"
    ABORT_BUDGET = "abort_budget"


@dataclass
class AcceptanceCriterion:
    id: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceCriterion:
        return cls(id=str(data["id"]), text=str(data["text"]))


@dataclass
class Task:
    id: str
    description: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    attempt: int = 1
    llm_calls: int = 0
    turns: int = 0
    files_written: list[str] = field(default_factory=list)
    summary: str = ""
    block_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "constraints": list(self.constraints),
            "state": self.state.value,
            "attempt": self.attempt,
            "llm_calls": self.llm_calls,
            "turns": self.turns,
            "files_written": list(self.files_written),
            "summary": self.summary,
            "block_reason": self.block_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=str(data["id"]),
            description=str(data["description"]),
            acceptance_criteria=[
                AcceptanceCriterion.from_dict(item)
                for item in data.get("acceptance_criteria", [])
            ],
            constraints=[str(item) for item in data.get("constraints", [])],
            state=TaskState(data.get("state", TaskState.PENDING.value)),
            attempt=int(data.get("attempt", 1)),
            llm_calls=int(data.get("llm_calls", 0)),
            turns=int(data.get("turns", 0)),
            files_written=[str(item) for item in data.get("files_written", [])],
            summary=str(data.get("summary", "")),
            block_reason=data.get("block_reason"),
        )


@dataclass
class Project:
    slug: str
    root: str

    def to_dict(self) -> dict[str, Any]:
        return {"slug": self.slug, "root": self.root}


@dataclass
class Run:
    id: str
    project_slug: str
    project_root: str
    request: str
    provider: str
    state: RunState = RunState.PLANNING
    budget_usd: float | None = None
    created_at: str = field(default_factory=utc_now_iso)
    block_reason: str | None = None
    tasks: list[Task] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_slug": self.project_slug,
            "project_root": self.project_root,
            "request": self.request,
            "provider": self.provider,
            "state": self.state.value,
            "budget_usd": self.budget_usd,
            "created_at": self.created_at,
            "block_reason": self.block_reason,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Run:
        return cls(
            id=str(data["id"]),
            project_slug=str(data["project_slug"]),
            project_root=str(data["project_root"]),
            request=str(data["request"]),
            provider=str(data["provider"]),
            state=RunState(data.get("state", RunState.PLANNING.value)),
            budget_usd=data.get("budget_usd"),
            created_at=str(data.get("created_at", utc_now_iso())),
            block_reason=data.get("block_reason"),
            tasks=[Task.from_dict(item) for item in data.get("tasks", [])],
        )


@dataclass
class Event:
    ts: str
    run_id: str
    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "run_id": self.run_id,
            "kind": self.kind,
            "data": self.data,
        }
