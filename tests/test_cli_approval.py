"""CLI approval gate: TTY detection and input handling (no real TTY needed)."""

from __future__ import annotations

import builtins
import sys

import pytest

from aiteam import cli
from aiteam.engine.policy import ApprovalOutcome

COMMAND = ["python", "-m", "pytest", "qa_tests", "-q"]


def _build_gate(monkeypatch, *, isatty: bool, answer: str | None, raise_eof: bool = False):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: isatty)
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)

    def fake_input() -> str:
        if raise_eof:
            raise EOFError
        if answer is None:
            raise AssertionError("input() must not be called when not a TTY")
        return answer

    monkeypatch.setattr(builtins, "input", fake_input)
    return cli.build_approval_gate()


def _request(gate):
    return gate.request(argv=COMMAND, cwd="c:/project", purpose="run tests")


@pytest.mark.parametrize("answer", ["y"])
def test_tty_accepts_lowercase_y(monkeypatch, answer):
    gate = _build_gate(monkeypatch, isatty=True, answer=answer)

    outcome, reason = _request(gate)

    assert outcome is ApprovalOutcome.APPROVED
    assert reason is None


@pytest.mark.parametrize("answer", ["Y", "yes", "1"])
def test_tty_rejects_everything_but_lowercase_y(monkeypatch, answer):
    gate = _build_gate(monkeypatch, isatty=True, answer=answer)

    outcome, reason = _request(gate)

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "user_denied"


def test_tty_accepts_empty_input_as_no(monkeypatch):
    gate = _build_gate(monkeypatch, isatty=True, answer="")

    outcome, reason = _request(gate)

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "user_denied"


def test_eof_is_denied(monkeypatch):
    gate = _build_gate(monkeypatch, isatty=True, answer=None, raise_eof=True)

    outcome, reason = _request(gate)

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "approval_input_unavailable"


def test_non_tty_denies_without_reading_input(monkeypatch):
    gate = _build_gate(monkeypatch, isatty=False, answer=None)

    outcome, reason = _request(gate)

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "non_interactive_denied"
