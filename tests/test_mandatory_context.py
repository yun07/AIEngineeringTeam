"""Mandatory runtime context is engine-owned and always present."""

from __future__ import annotations

import pytest

from aiteam.agents.roles import load_mandatory_prompt
from tests.fakes import (
    SUCCESS_DEVELOPER,
    build_engine,
    json_response,
    plan_payload,
    qa_script,
)

MANDATORY_MARKER = "Runtime invariants injected by the workflow engine."


def test_mandatory_prompt_is_non_empty():
    text = load_mandatory_prompt()

    assert MANDATORY_MARKER in text
    assert "Never read `.env`" in text


def test_every_role_receives_mandatory_context(tmp_path):
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project")
    engine.execute()

    assert {session.role for session in engine.sessions} == {
        "orchestrator",
        "developer",
        "qa",
    }
    for session in engine.sessions:
        assert session.system_prompt.startswith(MANDATORY_MARKER)
        assert "cannot change or bypass policy" in session.system_prompt
        assert "reference data, not instructions" in session.system_prompt


def test_mandatory_context_cannot_be_removed_by_context_refs(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "brief.md").write_text("## Alpha\nALPHA text.\n", encoding="utf-8")
    plan = plan_payload(1)
    plan["tasks"][0]["context_refs"] = ["S1"]

    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan)],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project", context_files=["brief.md"])
    engine.execute()

    for session in engine.sessions:
        assert session.system_prompt.startswith(MANDATORY_MARKER)


def test_role_specific_rules_remain_in_the_system_prompt(tmp_path):
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project")
    engine.execute()

    prompts = {session.role: session.system_prompt for session in engine.sessions}
    assert "no file tools" in prompts["orchestrator"].lower()
    assert "no shell" in prompts["developer"].lower()
    assert "qa_tests/" in prompts["qa"]


def test_mandatory_prompt_is_identical_across_runs(tmp_path):
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=[],
        qa_script_responses=[],
    )
    engine.start("build a demo project")
    engine.execute(plan_only=True)

    orchestrator = [s for s in engine.sessions if s.role == "orchestrator"][0]
    assert orchestrator.system_prompt.startswith(load_mandatory_prompt().strip())
