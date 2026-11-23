"""Engine-side QA evidence validation: coverage, negative checks and audit match."""

from __future__ import annotations

import json

import pytest

from aiteam.engine.evidence import (
    VerdictError,
    parse_verdict,
    validate_verdict,
)
from aiteam.models import AcceptanceCriterion, QaCheck, QaVerdict, Task
from aiteam.tools.shell import CommandRecord

COMMAND = "python -m pytest qa_tests -q"


def make_task(criteria=("C1", "C2")) -> Task:
    return Task(
        id="T1",
        description="do the work",
        acceptance_criteria=[
            AcceptanceCriterion(id=criterion, text=f"criterion {criterion}")
            for criterion in criteria
        ],
    )


def make_record(
    exit_code: int = 0,
    command_line: str = COMMAND,
    execution_id: str = "exec-1",
) -> CommandRecord:
    return CommandRecord(
        ts="2026-11-20T00:00:00Z",
        argv=command_line.split(),
        command_line=command_line,
        cwd="c:/project",
        decision="approved",
        purpose="run tests",
        exit_code=exit_code,
        output="1 passed",
        execution_id=execution_id,
    )


def check(
    criterion: str,
    kind: str = "positive",
    *,
    command: str = COMMAND,
    exit_code: int = 0,
    test_file: str | None = None,
    execution_id: str | None = "exec-1",
) -> QaCheck:
    return QaCheck(
        criterion=criterion,
        name=f"{criterion} {kind}",
        kind=kind,
        command=command,
        exit_code=exit_code,
        evidence="1 passed",
        test_file=test_file,
        execution_id=execution_id,
    )


def test_complete_evidence_is_accepted(tmp_path):
    qa_dir = tmp_path / "qa_tests"
    qa_dir.mkdir()
    (qa_dir / "test_demo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", test_file="qa_tests/test_demo.py"),
            check("C2", "negative", test_file="qa_tests/test_demo.py"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=tmp_path,
    )

    assert reasons == []


def test_missing_criterion_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[check("C1", "positive"), check("C1", "negative")],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,  # not reached when no test_file is declared
    )

    assert any("missing_criterion: C2" in reason for reason in reasons)


def test_missing_negative_check_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[check("C1", "positive"), check("C2", "positive")],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert "missing_negative_check" in reasons


def test_unknown_criterion_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive"),
            check("C2", "positive"),
            check("C9", "negative"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert any("unknown_criterion: C9" in reason for reason in reasons)


def test_no_command_executed_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[check("C1", "positive"), check("C2", "negative")],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert "no_command_executed" in reasons


def test_command_must_match_the_referenced_execution():
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", command="python -m pytest qa_tests -q -x"),
            check("C2", "negative"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert any("command_mismatch_for_execution" in reason for reason in reasons)


def test_missing_execution_id_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", execution_id=None),
            check("C2", "negative", execution_id=None),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert any("missing_execution_id" in reason for reason in reasons)


def test_unknown_execution_id_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", execution_id="exec-404"),
            check("C2", "negative", execution_id="exec-404"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert any("unknown_execution_id: exec-404" in reason for reason in reasons)


def test_one_execution_supports_multiple_checks_for_the_same_criterion_and_kind(
    tmp_path,
):
    """A single approved run legitimately backs several checks of one criterion."""
    qa_dir = tmp_path / "qa_tests"
    qa_dir.mkdir()
    (qa_dir / "test_demo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", test_file="qa_tests/test_demo.py"),
            check("C1", "positive", test_file="qa_tests/test_demo.py"),
            check("C2", "negative", test_file="qa_tests/test_demo.py"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=tmp_path,
    )

    assert reasons == []


def test_seven_check_one_execution_pattern_is_accepted(tmp_path):
    """The M3 shape: seven checks, one execution, shared ids, accepted."""
    qa_dir = tmp_path / "qa_tests"
    qa_dir.mkdir()
    (qa_dir / "test_demo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    test_file = "qa_tests/test_demo.py"
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", test_file=test_file),
            check("C1", "positive", test_file=test_file),
            check("C1", "negative", test_file=test_file),
            check("C2", "positive", test_file=test_file),
            check("C2", "positive", test_file=test_file),
            check("C2", "negative", test_file=test_file),
            check("C2", "negative", test_file=test_file),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=[test_file],
        project_root=tmp_path,
    )

    assert reasons == []


def test_exit_code_must_match_the_audit():
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", exit_code=0),
            check("C2", "negative"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record(exit_code=1)],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert any("exit_code_mismatch" in reason for reason in reasons)


def test_qa_test_files_must_exist(tmp_path):
    verdict = QaVerdict(
        verdict="pass",
        checks=[check("C1", "positive"), check("C2", "negative")],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_missing.py"],
        project_root=tmp_path,
    )

    assert any("qa_test_file_missing" in reason for reason in reasons)


def test_no_qa_test_files_written_is_rejected():
    verdict = QaVerdict(
        verdict="pass",
        checks=[check("C1", "positive"), check("C2", "negative")],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=[],
        project_root=None,
    )

    assert "no_qa_test_files_written" in reasons


def test_declared_test_file_must_live_under_qa_tests(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "test_demo.py").write_text("x = 1\n", encoding="utf-8")
    verdict = QaVerdict(
        verdict="pass",
        checks=[
            check("C1", "positive", test_file="src/test_demo.py"),
            check("C2", "negative"),
        ],
    )

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=tmp_path,
    )

    assert any("test_file_outside_qa_tests" in reason for reason in reasons)


def test_reported_fail_short_circuits():
    verdict = QaVerdict(verdict="fail", summary="wall collision not handled")

    reasons = validate_verdict(
        verdict=verdict,
        task=make_task(),
        audit=[make_record()],
        qa_test_files=["qa_tests/test_demo.py"],
        project_root=None,
    )

    assert reasons == ["qa_reported_fail: wall collision not handled"]


def test_parse_verdict_accepts_a_valid_payload():
    payload = {
        "verdict": "pass",
        "summary": "ok",
        "checks": [
            {
                "criterion": "C1",
                "name": "check",
                "kind": "positive",
                "command": COMMAND,
                "exit_code": 0,
                "evidence": "1 passed",
            }
        ],
        "unverified_requirements": [],
    }

    verdict = parse_verdict(json.dumps(payload))

    assert verdict.verdict == "pass"
    assert verdict.checks[0].criterion == "C1"


def test_parse_verdict_rejects_bad_kind():
    payload = {
        "verdict": "pass",
        "checks": [
            {
                "criterion": "C1",
                "kind": "maybe",
                "command": COMMAND,
                "exit_code": 0,
            }
        ],
    }

    with pytest.raises(VerdictError, match="kind"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_non_integer_exit_code():
    payload = {
        "verdict": "pass",
        "checks": [
            {
                "criterion": "C1",
                "kind": "positive",
                "command": COMMAND,
                "exit_code": "0",
            }
        ],
    }

    with pytest.raises(VerdictError, match="exit_code"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_unknown_verdict_word():
    with pytest.raises(VerdictError, match="pass"):
        parse_verdict(json.dumps({"verdict": "probably", "checks": []}))
