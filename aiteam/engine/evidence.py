"""Engine-side validation of QA verdicts.

QA is not trusted. The verdict is checked against the task's acceptance
criteria and against the engine's own command audit, and the engine, not QA,
decides whether the evidence is acceptable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from aiteam.models import QA_CHECK_KINDS, QaCheck, QaVerdict, Task
from aiteam.tools.shell import CommandRecord


class VerdictError(ValueError):
    """Raised when a QA reply is not a schema-valid verdict."""


def parse_verdict(text: str) -> QaVerdict:
    payload = _load_json(text)
    if not isinstance(payload, dict):
        raise VerdictError("verdict must be a JSON object")

    verdict = payload.get("verdict")
    if not isinstance(verdict, str) or verdict.strip().lower() not in ("pass", "fail"):
        raise VerdictError("verdict must be either 'pass' or 'fail'")

    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        raise VerdictError("checks must be a list")

    checks: list[QaCheck] = []
    for index, raw_check in enumerate(raw_checks, start=1):
        if not isinstance(raw_check, dict):
            raise VerdictError(f"check {index} must be an object")
        criterion = raw_check.get("criterion")
        if not isinstance(criterion, str) or not criterion.strip():
            raise VerdictError(f"check {index} needs a non-empty criterion id")
        kind = raw_check.get("kind")
        if not isinstance(kind, str) or kind.strip().lower() not in QA_CHECK_KINDS:
            raise VerdictError(
                f"check {index} kind must be one of {sorted(QA_CHECK_KINDS)}"
            )
        command = raw_check.get("command")
        if not isinstance(command, str):
            raise VerdictError(f"check {index} needs a command string")
        exit_code = raw_check.get("exit_code")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise VerdictError(f"check {index} needs an integer exit_code")
        test_file = raw_check.get("test_file")
        if test_file is not None and not isinstance(test_file, str):
            raise VerdictError(f"check {index} test_file must be a string")
        execution_id = raw_check.get("execution_id")
        if execution_id is not None and not isinstance(execution_id, str):
            raise VerdictError(f"check {index} execution_id must be a string")
        checks.append(
            QaCheck(
                criterion=criterion.strip(),
                name=str(raw_check.get("name", "")).strip(),
                kind=kind.strip().lower(),
                command=command,
                exit_code=exit_code,
                evidence=str(raw_check.get("evidence", "")),
                test_file=test_file,
                execution_id=execution_id,
            )
        )

    raw_unverified = payload.get("unverified_requirements") or []
    if not isinstance(raw_unverified, list) or not all(
        isinstance(item, str) for item in raw_unverified
    ):
        raise VerdictError("unverified_requirements must be a list of strings")

    return QaVerdict(
        verdict=verdict.strip().lower(),
        summary=str(payload.get("summary", "")),
        checks=checks,
        unverified_requirements=[item for item in raw_unverified],
    )


def normalize_command(command: str) -> str:
    return " ".join(command.split()).casefold()


def validate_verdict(
    *,
    verdict: QaVerdict,
    task: Task,
    audit: Sequence[CommandRecord],
    qa_test_files: Sequence[str],
    project_root: Path,
) -> list[str]:
    """Return the reasons the verdict is unacceptable. Empty means accepted."""
    if verdict.verdict != "pass":
        summary = verdict.summary.strip() or "no summary"
        return [f"qa_reported_{verdict.verdict}: {summary}"]

    reasons: list[str] = []
    if not verdict.checks:
        reasons.append("no_checks_reported")

    criteria_ids = {criterion.id for criterion in task.acceptance_criteria}
    covered = {check.criterion for check in verdict.checks}
    missing = sorted(criteria_ids - covered)
    if missing:
        reasons.append("missing_criterion: " + ", ".join(missing))
    unknown = sorted(covered - criteria_ids)
    if unknown:
        reasons.append("unknown_criterion: " + ", ".join(unknown))

    if not any(check.kind == "negative" for check in verdict.checks):
        reasons.append("missing_negative_check")

    if not audit:
        reasons.append("no_command_executed")
    audit_by_execution = {
        record.execution_id: record for record in audit if record.execution_id
    }

    for check in verdict.checks:
        if not check.command.strip():
            reasons.append(f"check_without_command: {check.name or check.criterion}")
            continue
        if not check.execution_id:
            reasons.append(f"missing_execution_id: {check.name or check.criterion}")
            continue
        record = audit_by_execution.get(check.execution_id)
        if record is None:
            reasons.append(f"unknown_execution_id: {check.execution_id}")
            continue
        if normalize_command(check.command) != normalize_command(record.command_line):
            reasons.append(
                "command_mismatch_for_execution: "
                f"{check.command} does not match {record.command_line}"
            )
        if record.exit_code != check.exit_code:
            reasons.append(
                "exit_code_mismatch: "
                f"{check.command} reported {check.exit_code} "
                f"observed {record.exit_code}"
            )
        if check.test_file and project_root is not None:
            reasons.extend(_test_file_reasons(check.test_file, project_root))

    if not qa_test_files:
        reasons.append("no_qa_test_files_written")
    elif project_root is not None:
        for relative in qa_test_files:
            if not (project_root / relative).is_file():
                reasons.append(f"qa_test_file_missing: {relative}")

    return reasons


def failure_evidence_reasons(
    *, verdict: QaVerdict, audit: Sequence[CommandRecord]
) -> list[str]:
    """Return the reasons a reported QA failure is not verifiable.

    An empty list means the engine itself observed a genuine non-zero exit code
    for a reported failing execution. A failure verdict that cannot be
    substantiated this way must not become a retryable ``QA_FAILED``.
    """
    if verdict.verdict != "fail":
        return ["not_a_failure_verdict"]
    if not verdict.checks:
        return ["no_checks_reported"]
    if not audit:
        return ["no_command_executed"]

    audit_by_execution = {
        record.execution_id: record for record in audit if record.execution_id
    }
    reasons: list[str] = []
    observed_failure = False
    for index, check in enumerate(verdict.checks, start=1):
        label = check.name or check.criterion or f"check {index}"
        if not check.command.strip():
            reasons.append(f"check_without_command: {label}")
            continue
        if not check.execution_id:
            reasons.append(f"missing_execution_id: {label}")
            continue
        record = audit_by_execution.get(check.execution_id)
        if record is None:
            reasons.append(f"unknown_execution_id: {check.execution_id}")
            continue
        if normalize_command(check.command) != normalize_command(record.command_line):
            reasons.append(
                "command_mismatch_for_execution: "
                f"{check.command} does not match {record.command_line}"
            )
            continue
        if record.timed_out:
            # A timeout is an infrastructure failure, not verifiable program
            # failure, and its exit code is None rather than a real non-zero.
            reasons.append(f"execution_timed_out: {check.execution_id}")
            continue
        if record.exit_code != check.exit_code:
            reasons.append(
                "exit_code_mismatch: "
                f"{check.command} reported {check.exit_code} "
                f"observed {record.exit_code}"
            )
            continue
        if (
            isinstance(record.exit_code, int)
            and not isinstance(record.exit_code, bool)
            and record.exit_code != 0
        ):
            observed_failure = True

    if not observed_failure:
        reasons.append("no_failed_execution_observed")
    return reasons


def _test_file_reasons(test_file: str, project_root: Path) -> list[str]:
    qa_root = (project_root / "qa_tests").resolve()
    candidate = (project_root / test_file).resolve()
    if candidate != qa_root and qa_root not in candidate.parents:
        return [f"test_file_outside_qa_tests: {test_file}"]
    if not candidate.is_file():
        return [f"test_file_missing: {test_file}"]
    return []


def _load_json(text: str) -> Any:
    if not isinstance(text, str) or not text.strip():
        raise VerdictError("verdict reply is empty")
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[: -len("```")]
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise VerdictError(f"verdict is not valid JSON: {exc}") from exc
