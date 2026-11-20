"""Shell tool and runner behaviour: no shell, pinned cwd, scrubbed env, limits."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aiteam.engine.policy import ApprovalGate, build_child_env
from aiteam.state.store import StateStore
from aiteam.tools.shell import (
    CommandDenied,
    RunResult,
    ShellTools,
    SubprocessRunner,
)
from tests.fakes import ScriptedRunner, approving_gate, denying_gate

TEST_COMMAND = ["python", "-m", "pytest", "qa_tests", "-q"]


def make_shell(
    tmp_path: Path,
    *,
    gate: ApprovalGate | None = None,
    runner=None,
    max_output_chars: int = 8000,
    timeout_seconds: float = 5.0,
) -> ShellTools:
    store = StateStore(tmp_path / "repo")
    return ShellTools(
        workspace_root=tmp_path / "repo" / "projects" / "demo",
        run_id="run-1",
        task_id="T1",
        session_id="session-1",
        gate=gate or approving_gate(),
        event_sink=lambda kind, data: None,
        store=store,
        runner=runner or ScriptedRunner(),
        max_output_chars=max_output_chars,
        timeout_seconds=timeout_seconds,
        target_files=("qa_tests/",),
    )


def test_policy_denied_command_never_reaches_the_runner(tmp_path):
    runner = ScriptedRunner()
    shell = make_shell(tmp_path, runner=runner)

    with pytest.raises(CommandDenied):
        shell.run(["pip", "install", "requests"])

    assert runner.calls == []
    assert shell.denials
    approvals = shell.store.read_approvals("run-1")
    assert approvals[0]["decision"] == "denied"
    assert approvals[0]["reason"].startswith("policy_deny")


def test_denied_approval_never_reaches_the_runner(tmp_path):
    runner = ScriptedRunner()
    gate = denying_gate()
    shell = make_shell(tmp_path, gate=gate, runner=runner)

    with pytest.raises(CommandDenied):
        shell.run(TEST_COMMAND)

    assert runner.calls == []
    assert len(gate.requested) == 1
    approvals = shell.store.read_approvals("run-1")
    assert approvals[0]["decision"] == "denied"
    assert approvals[0]["reason"] == "user_denied"


def test_approved_command_runs_once_and_is_audited(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=3, stdout="failure output")])
    gate = approving_gate()
    shell = make_shell(tmp_path, gate=gate, runner=runner)

    result = shell.run(TEST_COMMAND)

    assert len(runner.calls) == 1
    assert runner.calls[0]["cwd"] == str(shell.workspace_root)
    assert "OPENAI_API_KEY" not in runner.calls[0]["env"]
    assert runner.calls[0]["env"]["PYTHONUTF8"] == "1"
    assert "exit_code=3" in result
    assert shell.records[0].exit_code == 3
    execution_id = shell.records[0].execution_id
    assert execution_id
    assert f"execution_id={execution_id}" in result
    approvals = shell.store.read_approvals("run-1")
    assert approvals[0]["decision"] == "approved"


def test_informational_command_does_not_prompt(tmp_path):
    prompts: list[str] = []

    def approver(prompt: str) -> bool:
        prompts.append(prompt)
        return False

    gate = ApprovalGate(approver=approver, interactive=True)
    shell = make_shell(tmp_path, gate=gate)

    shell.run(["python", "--version"])

    assert prompts == []
    assert shell.records[0].decision == "auto"
    assert shell.store.read_approvals("run-1") == []


def test_shell_output_is_truncated_within_the_cap(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=0, stdout="y" * 500)])
    shell = make_shell(tmp_path, runner=runner, max_output_chars=50)

    shell.run(["python", "--version"])

    record = shell.records[0]
    assert record.truncated is True
    assert "[truncated command output]" in record.output
    assert len(record.output) <= 50


def test_output_exactly_at_the_limit_is_not_truncated(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=0, stdout="z" * 40)])
    shell = make_shell(tmp_path, runner=runner, max_output_chars=40)

    shell.run(["python", "--version"])

    record = shell.records[0]
    assert record.truncated is False
    assert record.output == "z" * 40
    assert len(record.output) == 40


def test_output_over_the_limit_is_capped_including_the_marker(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=0, stdout="w" * 500)])
    shell = make_shell(tmp_path, runner=runner, max_output_chars=40)

    shell.run(["python", "--version"])

    record = shell.records[0]
    assert record.truncated is True
    assert len(record.output) == 40
    assert record.output.endswith("...[truncated command output]")


def test_tiny_limit_still_caps_the_audit_output(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=0, stdout="v" * 500)])
    shell = make_shell(tmp_path, runner=runner, max_output_chars=10)

    shell.run(["python", "--version"])

    record = shell.records[0]
    assert record.truncated is True
    assert len(record.output) <= 10
    assert "trunc" in record.output


def test_tool_message_stays_within_the_session_cap(tmp_path):
    from aiteam.agents.base import AgentSession
    from aiteam.providers.base import ToolCall
    from aiteam.providers.fake import FakeProvider, text_response, tool_response

    runner = ScriptedRunner([RunResult(exit_code=0, stdout="q" * 2000)])
    shell = make_shell(tmp_path, runner=runner, max_output_chars=100)
    provider = FakeProvider(
        [
            tool_response(
                [
                    ToolCall(
                        id="call_1",
                        name="run_command",
                        arguments={"argv": ["python", "--version"]},
                    )
                ]
            ),
            text_response("done"),
        ]
    )
    session = AgentSession(
        role="qa",
        model="fake-qa",
        provider=provider,
        system_prompt="system",
        transcript_path=tmp_path / "session.jsonl",
        allowed_tools=frozenset({"run_command"}),
        max_tool_output_chars=100,
        tool_specs=shell.tool_specs(),
        tool_handlers=shell.handlers(),
        max_turns=6,
        max_llm_calls=6,
    )

    session.send("run the tests")

    tool_message = [
        message for message in provider.calls[1].messages if message.role == "tool"
    ][0]
    assert len(tool_message.content or "") <= 100


def test_real_runner_uses_pinned_cwd_and_scrubbed_env(tmp_path):
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    runner = SubprocessRunner()
    env = build_child_env(
        {
            "PATH": str(Path(sys.executable).parent),
            "SystemRoot": "C:\\Windows",
            "OPENAI_API_KEY": "sk-should-not-leak",
        }
    )

    result = runner.run(
        argv=[
            sys.executable,
            "-c",
            "import os; print(os.getcwd()); print(os.environ.get('OPENAI_API_KEY', 'missing'))",
        ],
        cwd=project,
        env=env,
        timeout=30,
    )

    assert result.exit_code == 0
    assert result.timed_out is False
    output = result.stdout.strip().splitlines()
    assert Path(output[0]) == project.resolve()
    assert output[1] == "missing"


def test_real_runner_does_not_interpret_shell_metacharacters(tmp_path):
    runner = SubprocessRunner()
    env = build_child_env({"PATH": str(Path(sys.executable).parent)})

    result = runner.run(
        argv=[sys.executable, "-c", "import sys; print(sys.argv[1])", "a&b; c"],
        cwd=tmp_path,
        env=env,
        timeout=30,
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "a&b; c"


def test_real_runner_reports_timeout(tmp_path):
    runner = SubprocessRunner()
    env = build_child_env({"PATH": str(Path(sys.executable).parent)})

    result = runner.run(
        argv=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=env,
        timeout=0.5,
    )

    assert result.timed_out is True
    assert result.exit_code is None
