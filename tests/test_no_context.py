"""A run without context files must not invent or auto-read context."""

from __future__ import annotations

from tests.fakes import (
    SUCCESS_DEVELOPER,
    build_engine,
    event_kinds,
    json_response,
    plan_payload,
    qa_script,
)

REPO_DOC_MARKERS = (
    "Token-efficient Context Management",
    "Git Workflow Rules",
    "Runtime invariants injected by the workflow engine.",
)


def test_run_without_context_has_no_manifest_or_prompt_block(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert run.context_manifest == []
    assert "context_loaded" not in event_kinds(store, run.id)
    assert not (store.run_dir(run.id) / "context" / "manifest.json").exists()

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "## Context" in report
    assert "No context files were supplied for this run." in report

    for session in engine.sessions:
        for message in session.messages:
            content = message.content or ""
            assert "BEGIN CONTEXT SOURCE" not in content
            assert "Token-efficient Context Management" not in content
            assert "Git Workflow Rules" not in content


def test_agent_prompts_do_not_read_repository_documents(tmp_path):
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project")
    engine.execute()

    for session in engine.sessions:
        assert "AGENTS.md" not in session.system_prompt
        assert "phase1-architecture-plan" not in session.system_prompt
        for message in session.messages:
            assert "phase1-architecture-plan" not in (message.content or "")
