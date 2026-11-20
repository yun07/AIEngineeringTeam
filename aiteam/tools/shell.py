"""Command execution for QA only, behind the engine's policy and approval gate.

Every execution follows the same sequence: classify, deny or prompt, record the
approval decision, execute without a shell, then record the result. A denied
command never reaches ``subprocess``.
"""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from aiteam.engine.policy import (
    ApprovalGate,
    ApprovalOutcome,
    Risk,
    build_child_env,
    classify_command,
)
from aiteam.models import ApprovalRecord, utc_now_iso
from aiteam.providers.base import ToolSpec


class CommandDenied(PermissionError):
    """Raised when policy or the human refuses one command execution."""


@dataclass
class RunResult:
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class CommandRunner(Protocol):
    def run(
        self,
        *,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        timeout: float,
    ) -> RunResult:
        """Execute one already-approved command."""


class SubprocessRunner:
    """Real runner: no shell, pinned cwd, scrubbed env, hard timeout."""

    def run(
        self,
        *,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        timeout: float,
    ) -> RunResult:
        try:
            completed = subprocess.run(
                list(argv),
                cwd=str(cwd),
                env=dict(env),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                exit_code=None,
                stdout=_as_text(exc.stdout),
                stderr=_as_text(exc.stderr),
                timed_out=True,
            )
        return RunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


@dataclass
class CommandRecord:
    """Structured audit entry, the only source of truth for QA evidence."""

    ts: str
    argv: list[str]
    command_line: str
    cwd: str
    decision: str
    purpose: str
    exit_code: int | None = None
    output: str = ""
    truncated: bool = False
    timed_out: bool = False
    denied_reason: str | None = None
    execution_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "argv": list(self.argv),
            "command_line": self.command_line,
            "cwd": self.cwd,
            "decision": self.decision,
            "purpose": self.purpose,
            "exit_code": self.exit_code,
            "output": self.output,
            "truncated": self.truncated,
            "timed_out": self.timed_out,
            "denied_reason": self.denied_reason,
            "execution_id": self.execution_id,
        }


@dataclass
class ShellTools:
    """The single command tool for the QA role."""

    workspace_root: Path
    run_id: str
    task_id: str
    session_id: str
    gate: ApprovalGate
    event_sink: Callable[[str, dict[str, Any]], None]
    store: Any
    runner: CommandRunner | None = None
    purpose: str = "run the QA test suite for this task"
    max_output_chars: int = 8000
    timeout_seconds: float = 120
    target_files: Sequence[str] = field(default_factory=tuple)
    records: list[CommandRecord] = field(default_factory=list)
    denials: list[CommandRecord] = field(default_factory=list)

    def tool_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="run_command",
                description=(
                    "Run the approved project test command. Provide the exact "
                    "argument vector; policy decides whether it may run."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "argv": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["argv"],
                },
            )
        ]

    def handlers(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {"run_command": self._run_handler}

    def _run_handler(self, arguments: dict[str, Any]) -> str:
        argv = arguments.get("argv")
        if not isinstance(argv, list) or not argv:
            raise ValueError("argv must be a non-empty list of strings")
        if not all(isinstance(part, str) and part for part in argv):
            raise ValueError("argv entries must be non-empty strings")
        return self.run(argv)

    def run(self, argv: Sequence[str]) -> str:
        argv_list = [str(part) for part in argv]
        command_line = subprocess.list2cmdline(argv_list)
        decision = classify_command(argv_list)
        cwd = str(self.workspace_root)

        if decision.risk is Risk.DENY:
            record = self._record(
                argv_list,
                command_line,
                cwd,
                decision="denied",
                denied_reason=f"policy_deny: {decision.reason}",
            )
            self.denials.append(record)
            self._write_approval(command_line, cwd, "denied", f"policy_deny: {decision.reason}")
            self._emit("command_denied", record)
            raise CommandDenied(f"policy denied: {decision.reason}")

        if decision.risk is Risk.CONFIRM:
            outcome, reason = self.gate.request(
                argv=argv_list,
                cwd=cwd,
                purpose=self.purpose,
                target_files=list(self.target_files),
            )
            self._write_approval(
                command_line,
                cwd,
                outcome.value,
                reason or f"confirm: {decision.reason}",
            )
            if outcome is ApprovalOutcome.DENIED:
                record = self._record(
                    argv_list,
                    command_line,
                    cwd,
                    decision="denied",
                    denied_reason=f"approval_denied: {reason}",
                    purpose=self.purpose,
                )
                self.denials.append(record)
                self._emit("command_denied", record)
                raise CommandDenied(f"approval denied: {reason}")

        runner = self.runner or SubprocessRunner()
        result = runner.run(
            argv=argv_list,
            cwd=self.workspace_root,
            env=build_child_env(),
            timeout=self.timeout_seconds,
        )

        output, truncated = _cap_command_output(
            (result.stdout + result.stderr).strip(), self.max_output_chars
        )

        record = self._record(
            argv_list,
            command_line,
            cwd,
            decision="approved" if decision.risk is Risk.CONFIRM else "auto",
            exit_code=result.exit_code,
            output=output,
            truncated=truncated,
            timed_out=result.timed_out,
            purpose=self.purpose,
            execution_id=uuid.uuid4().hex[:12],
        )
        self.records.append(record)
        self._emit("command_executed", record)
        return _format_result(record)

    def _record(
        self,
        argv: Sequence[str],
        command_line: str,
        cwd: str,
        *,
        decision: str,
        purpose: str | None = None,
        exit_code: int | None = None,
        output: str = "",
        truncated: bool = False,
        timed_out: bool = False,
        denied_reason: str | None = None,
        execution_id: str | None = None,
    ) -> CommandRecord:
        return CommandRecord(
            ts=utc_now_iso(),
            argv=list(argv),
            command_line=command_line,
            cwd=cwd,
            decision=decision,
            purpose=purpose or self.purpose,
            exit_code=exit_code,
            output=output,
            truncated=truncated,
            timed_out=timed_out,
            denied_reason=denied_reason,
            execution_id=execution_id,
        )

    def _write_approval(
        self, command_line: str, cwd: str, decision: str, reason: str | None
    ) -> None:
        self.store.append_approval(
            ApprovalRecord(
                ts=utc_now_iso(),
                run_id=self.run_id,
                task_id=self.task_id,
                session_id=self.session_id,
                command_line=command_line,
                cwd=cwd,
                purpose=self.purpose,
                decision=decision,
                reason=reason,
            )
        )

    def _emit(self, kind: str, record: CommandRecord) -> None:
        self.event_sink(kind, record.to_dict())


TRUNCATION_MARKER = "\n...[truncated command output]"
SHORT_TRUNCATION_MARKER = "...[truncated]"


def _cap_command_output(text: str, limit: int) -> tuple[str, bool]:
    """Cap the audit output, marker included, to ``limit`` characters."""
    if limit < 1:
        return "", bool(text)
    if len(text) <= limit:
        return text, False
    if len(TRUNCATION_MARKER) < limit:
        return text[: limit - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER, True
    if len(SHORT_TRUNCATION_MARKER) < limit:
        return (
            text[: limit - len(SHORT_TRUNCATION_MARKER)] + SHORT_TRUNCATION_MARKER,
            True,
        )
    return SHORT_TRUNCATION_MARKER[:limit], True


def _format_result(record: CommandRecord) -> str:
    exit_code = "timeout" if record.timed_out else str(record.exit_code)
    return (
        f"execution_id={record.execution_id}\n"
        f"exit_code={exit_code}\n"
        f"command={record.command_line}\n"
        f"cwd={record.cwd}\n"
        f"output:\n{record.output}"
    )
