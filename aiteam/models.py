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


QA_CHECK_KINDS = frozenset({"positive", "negative"})


@dataclass
class QaCheck:
    """One verification check reported by QA and validated by the engine.

    ``execution_id`` is the engine-owned identifier of the command execution
    this check refers to. QA can only echo it; it cannot create or edit the
    audit record behind it.
    """

    criterion: str
    name: str
    kind: str
    command: str
    exit_code: int
    evidence: str = ""
    test_file: str | None = None
    execution_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "name": self.name,
            "kind": self.kind,
            "command": self.command,
            "exit_code": self.exit_code,
            "evidence": self.evidence,
            "test_file": self.test_file,
            "execution_id": self.execution_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QaCheck:
        return cls(
            criterion=str(data["criterion"]),
            name=str(data.get("name", "")),
            kind=str(data.get("kind", "")),
            command=str(data.get("command", "")),
            exit_code=int(data.get("exit_code", -1)),
            evidence=str(data.get("evidence", "")),
            test_file=data.get("test_file"),
            execution_id=data.get("execution_id"),
        )


@dataclass
class QaVerdict:
    verdict: str
    summary: str = ""
    checks: list[QaCheck] = field(default_factory=list)
    unverified_requirements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "summary": self.summary,
            "checks": [check.to_dict() for check in self.checks],
            "unverified_requirements": list(self.unverified_requirements),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QaVerdict:
        return cls(
            verdict=str(data.get("verdict", "")),
            summary=str(data.get("summary", "")),
            checks=[QaCheck.from_dict(item) for item in data.get("checks", [])],
            unverified_requirements=[
                str(item) for item in data.get("unverified_requirements", [])
            ],
        )


@dataclass
class ApprovalRecord:
    """One human decision for one specific command execution."""

    ts: str
    run_id: str
    task_id: str
    session_id: str
    command_line: str
    cwd: str
    purpose: str
    decision: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "command_line": self.command_line,
            "cwd": self.cwd,
            "purpose": self.purpose,
            "decision": self.decision,
            "reason": self.reason,
        }


@dataclass
class UsageRecord:
    """One provider call, priced from provider-reported usage."""

    ts: str
    run_id: str
    task_id: str
    role: str
    model: str
    input_tokens: int
    output_tokens: int
    usd: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "role": self.role,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "usd": self.usd,
        }


@dataclass
class Task:
    id: str
    description: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    attempt: int = 1
    llm_calls: int = 0
    turns: int = 0
    files_written: list[str] = field(default_factory=list)
    summary: str = ""
    block_reason: str | None = None
    qa_verdict: QaVerdict | None = None
    qa_test_files: list[str] = field(default_factory=list)
    qa_failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "constraints": list(self.constraints),
            "context_refs": list(self.context_refs),
            "state": self.state.value,
            "attempt": self.attempt,
            "llm_calls": self.llm_calls,
            "turns": self.turns,
            "files_written": list(self.files_written),
            "summary": self.summary,
            "block_reason": self.block_reason,
            "qa_verdict": self.qa_verdict.to_dict() if self.qa_verdict else None,
            "qa_test_files": list(self.qa_test_files),
            "qa_failure_reason": self.qa_failure_reason,
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
            context_refs=[str(item) for item in data.get("context_refs", [])],
            state=TaskState(data.get("state", TaskState.PENDING.value)),
            attempt=int(data.get("attempt", 1)),
            llm_calls=int(data.get("llm_calls", 0)),
            turns=int(data.get("turns", 0)),
            files_written=[str(item) for item in data.get("files_written", [])],
            summary=str(data.get("summary", "")),
            block_reason=data.get("block_reason"),
            qa_verdict=(
                QaVerdict.from_dict(data["qa_verdict"])
                if data.get("qa_verdict")
                else None
            ),
            qa_test_files=[str(item) for item in data.get("qa_test_files", [])],
            qa_failure_reason=data.get("qa_failure_reason"),
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
    context_manifest: list[dict[str, Any]] = field(default_factory=list)
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
            "context_manifest": list(self.context_manifest),
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
            context_manifest=list(data.get("context_manifest", [])),
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
