"""Task-specific context scoping and reference validation."""

from __future__ import annotations

from aiteam.models import RunState
from tests.fakes import (
    SUCCESS_DEVELOPER,
    build_engine,
    event_kinds,
    json_response,
    plan_payload,
    qa_script,
)

CONTEXT = "# Brief\n\n## Alpha\nALPHA_SENTINEL detail.\n\n## Beta\nBETA_SENTINEL detail.\n"


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "brief.md").write_text(CONTEXT, encoding="utf-8")
    return repo


def _plan(refs):
    payload = plan_payload(1)
    payload["tasks"][0]["context_refs"] = refs
    return payload


def _calls_for(provider, role):
    return [call for call in provider.calls if call.role == role]


def test_developer_scope_and_full_qa_context(tmp_path):
    _repo(tmp_path)
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(_plan(["S2"]))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project", context_files=["brief.md"])
    engine.execute()

    provider = engine._provider
    orchestrator_bundle = _calls_for(provider, "orchestrator")[0].messages[0].content
    developer_bundle = _calls_for(provider, "developer")[0].messages[0].content
    qa_bundle_text = _calls_for(provider, "qa")[0].messages[0].content

    assert "ALPHA_SENTINEL" in orchestrator_bundle
    assert "BETA_SENTINEL" in orchestrator_bundle

    assert "ALPHA_SENTINEL" in developer_bundle
    assert "BETA_SENTINEL" not in developer_bundle

    # M7 fix: QA always receives the full context bundle, so a normative test
    # plan is never lost when the Orchestrator scopes it to another task.
    assert "ALPHA_SENTINEL" in qa_bundle_text
    assert "BETA_SENTINEL" in qa_bundle_text


def test_task_without_refs_gets_no_context_sections(tmp_path):
    _repo(tmp_path)
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project", context_files=["brief.md"])
    engine.execute()

    developer_bundle = _calls_for(engine._provider, "developer")[0].messages[0].content
    assert "ALPHA_SENTINEL" not in developer_bundle
    assert "No project context was supplied for this task." in developer_bundle


def test_unknown_context_ref_is_repaired_once(tmp_path):
    _repo(tmp_path)
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[
            json_response(_plan(["S99"])),
            json_response(_plan(["S2"])),
        ],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    run = engine.start("build a demo project", context_files=["brief.md"])
    result = engine.execute()

    assert result.state is RunState.COMPLETED
    assert "plan_invalid" in event_kinds(store, run.id)


def test_context_refs_without_any_context_are_rejected(tmp_path):
    engine, store = build_engine(
        tmp_path,
        orchestrator_script=[
            json_response(_plan(["S2"])),
            json_response(_plan(["S2"])),
        ],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    run = engine.start("build a demo project")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "plan_invalid" in (result.block_reason or "")
    assert "no context files were supplied" in (result.block_reason or "")
    assert "plan_invalid" in event_kinds(store, run.id)


def test_developer_and_qa_transcripts_stay_separate(tmp_path):
    _repo(tmp_path)
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(_plan(["S3"]))],
        developer_script=SUCCESS_DEVELOPER,
        qa_script_responses=qa_script(),
    )
    engine.start("build a demo project", context_files=["brief.md"])
    engine.execute()

    developer = [s for s in engine.sessions if s.role == "developer"][0]
    qa = [s for s in engine.sessions if s.role == "qa"][0]

    assert developer.transcript_path != qa.transcript_path
    assert all(message not in qa.messages for message in developer.messages)
    # QA gets every supplied section (M7 fix), but no Developer transcript.
    assert "BETA_SENTINEL" in qa.messages[0].content
    assert "ALPHA_SENTINEL" in qa.messages[0].content
