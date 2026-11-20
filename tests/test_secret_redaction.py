"""SEC-1 to SEC-11: exact secret values must not reach durable surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiteam.agents.base import AgentSession
from aiteam.engine.policy import build_child_env
from aiteam.engine.workflow import WorkflowEngine
from aiteam.models import Run, RunState
from aiteam.providers.base import LLMResponse, ToolCall, Usage
from aiteam.providers.fake import FakeProvider, text_response, tool_response
from aiteam.secrets import SecretBoundary, SecretError, resolve_api_key
from aiteam.state.store import StateStore
from aiteam.tools.filesystem import FileTools, Workspace
from tests.fakes import (
    StubProvider,
    approving_gate,
    make_config,
)

KEY = "sk-dummy-redaction-key-1234567890"


def _boundary() -> SecretBoundary:
    return SecretBoundary([KEY])


def _session(
    tmp_path: Path,
    responses,
    boundary: SecretBoundary,
    *,
    allowed=("write_file",),
):
    workspace = Workspace(tmp_path / "project")
    tools = FileTools(workspace)
    session = AgentSession(
        role="developer",
        model="fake-developer",
        provider=FakeProvider(responses=list(responses)),
        system_prompt="system",
        transcript_path=tmp_path / "session.jsonl",
        allowed_tools=frozenset(allowed),
        redact_values=boundary.redact,
        contains_secret=boundary.contains_any,
        tool_specs=tuple(tools.tool_specs()),
        tool_handlers=tools.handlers(),
        max_turns=5,
        max_llm_calls=5,
    )
    return session, workspace


def _engine(tmp_path: Path, provider, boundary: SecretBoundary):
    repo = tmp_path / "repo"
    store = StateStore(repo)
    engine = WorkflowEngine(
        config=make_config(),
        provider=provider,
        store=store,
        project_root=repo / "projects" / "demo",
        project_slug="demo",
        approval_gate=approving_gate(),
        secret_boundary=boundary,
    )
    return engine, store


def test_secret_boundary_repr_never_exposes_the_value():
    boundary = _boundary()

    assert KEY not in repr(boundary)
    assert repr(boundary) == "SecretBoundary(values=1)"


def test_sec1_provider_error_is_redacted_in_block_reason_and_persisted_files(
    tmp_path,
):
    boundary = _boundary()
    # Fake mode requires a fake-classified provider; the stub still raises the
    # provider error this test is about.
    provider = StubProvider(
        {}, error=RuntimeError(f"provider said {KEY}"), name="fake"
    )
    engine, store = _engine(tmp_path, provider, boundary)

    run = engine.start("clean request")
    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert KEY not in (result.block_reason or "")
    for path in (tmp_path / "repo").rglob("*"):
        if path.is_file():
            assert KEY not in path.read_text(encoding="utf-8")
    assert run.id


def test_sec2_response_text_is_redacted_in_messages_and_transcript(tmp_path):
    boundary = _boundary()
    session, _ = _session(
        tmp_path, [text_response(f"model output {KEY}")], boundary
    )

    output = session.send("hello")

    assert KEY not in output
    assert all(KEY not in (message.content or "") for message in session.messages)
    assert KEY not in (tmp_path / "session.jsonl").read_text(encoding="utf-8")


def test_sec6_a_tool_call_containing_a_key_is_rejected_before_dispatch(tmp_path):
    boundary = _boundary()
    call = ToolCall(
        id="call_write",
        name="write_file",
        arguments={"path": "leak.txt", "content": f"leaked {KEY}"},
    )
    session, workspace = _session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        boundary,
    )

    session.send("write the file")

    assert not (workspace.root / "leak.txt").exists()
    invocation = session.tool_invocations[0]
    assert invocation.error is not None
    assert "configured secret" in invocation.error
    assert KEY not in (tmp_path / "session.jsonl").read_text(encoding="utf-8")
    assert KEY not in str(workspace.root)


def test_sec6_nested_tool_arguments_are_also_checked(tmp_path):
    boundary = _boundary()
    call = ToolCall(
        id="call_nested",
        name="write_file",
        arguments={"path": "nested.txt", "content": {"text": KEY}},
    )
    session, workspace = _session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        boundary,
    )

    session.send("write")

    assert not (workspace.root / "nested.txt").exists()
    assert "configured secret" in (session.tool_invocations[0].error or "")
    assert KEY not in (tmp_path / "session.jsonl").read_text(encoding="utf-8")


def test_sec7_role_messages_and_handoff_material_contain_no_key(tmp_path):
    boundary = _boundary()
    session, _ = _session(
        tmp_path, [text_response(f"assistant text {KEY}")], boundary
    )

    session.send(f"prompt with {KEY}")

    joined = "\n".join(message.content or "" for message in session.messages)
    assert KEY not in joined
    assert KEY not in (tmp_path / "session.jsonl").read_text(encoding="utf-8")


def test_sec8_persisted_run_and_index_output_are_redacted(tmp_path):
    boundary = _boundary()
    repo = tmp_path / "repo"
    store = StateStore(repo, redactor=boundary.redact)
    run = Run(
        id="run-1",
        project_slug="demo",
        project_root=str(repo),
        request=f"request contains {KEY}",
        provider="fake",
    )

    store.save(run)
    store.write_report(run.id, f"report contains {KEY}")

    index = (repo / "state" / "index.json").read_text(encoding="utf-8")
    report = (repo / "runs" / run.id / "report.md").read_text(encoding="utf-8")
    assert KEY not in index
    assert KEY not in report
    assert "[REDACTED]" in index


def test_sec9_child_environment_never_inherits_the_key():
    child = build_child_env(
        {
            "OPENAI_API_KEY": KEY,
            "PATH": "C:/tools",
            "PYTHONPATH": ".",
        }
    )

    assert "OPENAI_API_KEY" not in child
    assert KEY not in child.values()


def test_sec10_missing_key_fails_before_a_client_exists(tmp_path):
    with pytest.raises(SecretError, match="not set"):
        resolve_api_key(
            environ={},
            root=tmp_path,
            dotenv_path=tmp_path / "missing.env",
        )


def test_env_file_is_read_inside_the_repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text(f"OPENAI_API_KEY={KEY}\n", encoding="utf-8")

    value = resolve_api_key(
        environ={}, root=repo, dotenv_path=Path(".env")
    )

    assert value == KEY


def test_env_symlink_to_outside_the_repository_is_refused(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.env"
    outside.write_text(f"OPENAI_API_KEY={KEY}\n", encoding="utf-8")
    link = repo / ".env"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted in this environment")

    with pytest.raises(SecretError, match="outside the repository"):
        resolve_api_key(environ={}, root=repo, dotenv_path=Path(".env"))


def test_environment_wins_over_the_dotenv_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")

    value = resolve_api_key(
        environ={"OPENAI_API_KEY": "from-environment"},
        root=repo,
        dotenv_path=Path(".env"),
    )

    assert value == "from-environment"


def test_sec11_context_with_the_key_is_refused_before_a_run_directory(tmp_path):
    boundary = _boundary()
    engine, store = _engine(tmp_path, FakeProvider(responses=[]), boundary)
    repo = tmp_path / "repo"
    context_dir = repo / "context"
    context_dir.mkdir()
    (context_dir / "leak.md").write_text(
        f"## Notes\n\n{KEY}\n", encoding="utf-8"
    )
    before = set(store.runs_dir.iterdir())

    with pytest.raises(SecretError, match="context file"):
        engine.start("clean request", context_files=["context/leak.md"])

    assert set(store.runs_dir.iterdir()) == before
    assert store.read_events() == []


def test_sec11_request_with_the_key_is_refused_before_a_run_directory(tmp_path):
    boundary = _boundary()
    engine, store = _engine(tmp_path, FakeProvider(responses=[]), boundary)
    before = set(store.runs_dir.iterdir())

    with pytest.raises(SecretError, match="user request"):
        engine.start(f"please use {KEY}")

    assert set(store.runs_dir.iterdir()) == before
    assert store.read_events() == []


def test_missing_usage_is_not_silently_turned_into_zero(tmp_path):
    session = AgentSession(
        role="developer",
        model="fake-developer",
        provider=FakeProvider(
            responses=[LLMResponse(text="ok", usage=None)]
        ),
        system_prompt="system",
        transcript_path=tmp_path / "session.jsonl",
        allowed_tools=frozenset(),
    )

    assert session.send("hello") == "ok"
    assert session.usage == Usage()
    assert '"usage": null' in (tmp_path / "session.jsonl").read_text(
        encoding="utf-8"
    )
