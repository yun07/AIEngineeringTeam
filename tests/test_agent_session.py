"""Agent session: tool loop, isolation between sessions and execution limits."""

from __future__ import annotations

import re

import pytest

from aiteam.agents.base import AgentSession, LimitExceeded
from aiteam.agents.roles import (
    DEVELOPER_TOOLS,
    FORBIDDEN_ROLE_TOOLS,
    ORCHESTRATOR,
    QA_TOOLS,
)
from aiteam.providers.base import ToolCall, Usage
from aiteam.providers.fake import FakeProvider, text_response, tool_response
from aiteam.tools.filesystem import FileTools, Workspace


@pytest.fixture
def developer_tools(tmp_path):
    return FileTools(Workspace(tmp_path / "project", write_deny_subpaths=("qa_tests",)))


def make_session(
    tmp_path,
    responses,
    *,
    tools=(),
    handlers=None,
    max_turns=6,
    max_llm_calls=6,
    max_tool_output_chars=8000,
    transcript="session.jsonl",
):
    provider = FakeProvider(list(responses))
    return AgentSession(
        role="developer",
        model="fake-developer",
        provider=provider,
        system_prompt="You are a test system prompt.",
        transcript_path=tmp_path / transcript,
        allowed_tools=frozenset(spec.name for spec in tools),
        max_tool_output_chars=max_tool_output_chars,
        tool_specs=tuple(tools),
        tool_handlers=dict(handlers or {}),
        max_turns=max_turns,
        max_llm_calls=max_llm_calls,
    )


def test_developer_role_has_no_shell_tool():
    assert set(DEVELOPER_TOOLS) == {"read_file", "write_file", "list_files"}
    assert set(DEVELOPER_TOOLS).isdisjoint(FORBIDDEN_ROLE_TOOLS)
    assert ORCHESTRATOR.tools == ()


def test_qa_role_owns_the_only_command_tool():
    assert set(QA_TOOLS) == {
        "read_file",
        "list_files",
        "write_file",
        "run_command",
    }
    for shell_name in ("run_shell", "shell", "exec", "cmd", "powershell"):
        assert shell_name not in QA_TOOLS


def test_sessions_do_not_share_messages_or_transcripts(tmp_path):
    first = make_session(tmp_path, [text_response("first reply")], transcript="a.jsonl")
    second = make_session(tmp_path, [text_response("second reply")], transcript="b.jsonl")

    assert first.send("hello") == "first reply"
    assert second.send("hello") == "second reply"

    assert first.session_id != second.session_id
    assert first.transcript_path != second.transcript_path
    assert len(first.messages) == 2
    assert len(second.messages) == 2

    first_log = first.transcript_path.read_text(encoding="utf-8")
    second_log = second.transcript_path.read_text(encoding="utf-8")
    assert "first reply" in first_log
    assert "second reply" not in first_log
    assert "first reply" not in second_log


def test_tool_loop_writes_a_file_and_accumulates_usage(tmp_path, developer_tools):
    call = ToolCall(
        id="call_1",
        name="write_file",
        arguments={"path": "notes.md", "content": "hello\n"},
    )
    session = make_session(
        tmp_path,
        [
            tool_response([call], usage=Usage(60, 30)),
            text_response("done", usage=Usage(20, 10)),
        ],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
    )

    assert session.send("write notes.md") == "done"

    assert (tmp_path / "project" / "notes.md").read_text(encoding="utf-8") == "hello\n"
    assert session.llm_calls == 2
    assert session.turns == 2
    assert session.usage == Usage(80, 40)
    assert session.tool_invocations[0].error is None


def test_turn_cap_stops_the_session(tmp_path, developer_tools):
    responses = [
        tool_response([ToolCall(id=f"call_{index}", name="list_files", arguments={})])
        for index in range(6)
    ]
    session = make_session(
        tmp_path,
        responses,
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_turns=2,
        max_llm_calls=99,
    )

    with pytest.raises(LimitExceeded, match="max_turns_per_session"):
        session.send("loop forever")


def test_llm_call_cap_stops_the_session(tmp_path, developer_tools):
    responses = [
        tool_response([ToolCall(id=f"call_{index}", name="list_files", arguments={})])
        for index in range(6)
    ]
    session = make_session(
        tmp_path,
        responses,
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_turns=99,
        max_llm_calls=2,
    )

    with pytest.raises(LimitExceeded, match="max_llm_calls_per_task"):
        session.send("loop forever")


def test_denied_write_is_reported_as_a_tool_error(tmp_path, developer_tools):
    call = ToolCall(
        id="call_1",
        name="write_file",
        arguments={"path": "../escape.md", "content": "nope"},
    )
    session = make_session(
        tmp_path,
        [tool_response([call]), text_response("stoped")],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
    )

    session.send("escape the workspace")

    assert session.tool_invocations[0].error is not None
    assert "escapes the workspace" in (session.tool_invocations[0].error or "")
    assert not (tmp_path / "escape.md").exists()


def test_unknown_tool_is_refused(tmp_path):
    call = ToolCall(id="call_1", name="run_command", arguments={"argv": ["pip", "install", "x"]})
    session = make_session(tmp_path, [tool_response([call]), text_response("refused")])

    session.send("install a package")

    assert session.tool_invocations[0].error is not None
    assert "not permitted" in (session.tool_invocations[0].error or "")


def test_truncation_marker_reports_the_exact_number_of_removed_characters(
    tmp_path, developer_tools
):
    original = "C" * 200
    (tmp_path / "project" / "big.txt").write_text(original, encoding="utf-8")
    call = ToolCall(id="call_1", name="read_file", arguments={"path": "big.txt"})
    session = make_session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_tool_output_chars=100,
    )

    session.send("read the big file")

    tool_message = [
        message
        for message in session.provider.calls[1].messages
        if message.role == "tool"
    ][0]
    content = tool_message.content or ""
    match = re.search(r"truncated (\d+) characters", content)
    assert match is not None
    kept = content.index("\n...[truncated")
    assert int(match.group(1)) == len(original) - kept
    assert len(content) <= 100
    assert content.startswith("C" * kept)


def test_read_file_output_is_capped_before_reaching_the_model(tmp_path, developer_tools):
    (tmp_path / "project" / "big.txt").write_text("A" * 500, encoding="utf-8")
    call = ToolCall(id="call_1", name="read_file", arguments={"path": "big.txt"})
    session = make_session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_tool_output_chars=40,
    )

    session.send("read the big file")

    tool_message = [
        message
        for message in session.provider.calls[1].messages
        if message.role == "tool"
    ][0]
    content = tool_message.content or ""
    assert len(content) <= 40
    assert content.startswith("A" * 26)
    assert content.endswith("...[truncated]")
    assert "A" * 41 not in content
    assert "A" * 500 not in content


def test_list_files_output_is_capped_before_reaching_the_model(tmp_path, developer_tools):
    for index in range(30):
        (tmp_path / "project" / f"file_{index:02d}.txt").write_text(
            "x", encoding="utf-8"
        )
    call = ToolCall(id="call_1", name="list_files", arguments={"path": "."})
    session = make_session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_tool_output_chars=60,
    )

    session.send("list the files")

    tool_message = [
        message
        for message in session.provider.calls[1].messages
        if message.role == "tool"
    ][0]
    content = tool_message.content or ""
    assert len(content) <= 60
    assert "truncated" in content
    assert "file_29.txt" not in content
    assert "file_00.txt" in content


def test_output_cap_holds_when_the_marker_barely_fits(tmp_path, developer_tools):
    (tmp_path / "project" / "big.txt").write_text("B" * 500, encoding="utf-8")
    call = ToolCall(id="call_1", name="read_file", arguments={"path": "big.txt"})
    session = make_session(
        tmp_path,
        [tool_response([call]), text_response("done")],
        tools=developer_tools.tool_specs(),
        handlers=developer_tools.handlers(),
        max_tool_output_chars=10,
    )

    session.send("read the big file")

    tool_message = [
        message
        for message in session.provider.calls[1].messages
        if message.role == "tool"
    ][0]
    content = tool_message.content or ""
    assert len(content) <= 10
    assert "trunc" in content
    assert "B" not in content
