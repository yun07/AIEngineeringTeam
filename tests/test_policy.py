"""Command policy: exact argv matching, denial classes and the approval gate."""

from __future__ import annotations

from aiteam.agents.roles import (
    DEVELOPER_TOOLS,
    ORCHESTRATOR_TOOLS,
    QA_TOOLS,
    forbidden_tools_for,
    get_role,
)
from aiteam.engine.policy import (
    ApprovalGate,
    ApprovalOutcome,
    Risk,
    build_child_env,
    classify_command,
)

TEST_COMMAND = ["python", "-m", "pytest", "qa_tests", "-q"]


def test_informational_allowlist_is_exact():
    assert classify_command(["python", "--version"]).risk is Risk.AUTO
    assert classify_command(["git", "status", "--short"]).risk is Risk.AUTO
    assert classify_command(["python", "-V"]).risk is Risk.DENY
    assert classify_command(["git", "status"]).risk is Risk.DENY


def test_prefix_matching_is_never_a_grant():
    assert classify_command(["python", "evil.py"]).risk is Risk.DENY
    assert (
        classify_command(["python", "-m", "pytest", "qa_tests", "-q", "--ignore=qa_tests"]).risk
        is Risk.DENY
    )
    assert classify_command(["python", "-m", "pytest", "qa_tests"]).risk is Risk.DENY


def test_only_the_exact_test_command_is_confirm():
    decision = classify_command(TEST_COMMAND)
    assert decision.risk is Risk.CONFIRM


def test_package_installation_is_denied_in_every_form():
    cases = [
        ["pip", "install", "requests"],
        ["pip3", "install", "requests"],
        ["python", "-m", "pip", "install", "requests"],
        ["conda", "install", "-n", "ai-team", "pytest"],
        ["mamba", "install", "pytest"],
        ["npm", "install"],
        ["npm", "install", "left-pad"],
        ["yarn", "add", "x"],
        ["pnpm", "add", "x"],
        ["winget", "install", "x"],
        ["choco", "install", "x"],
        ["uv", "pip", "install", "x"],
        ["poetry", "add", "x"],
    ]
    for argv in cases:
        assert classify_command(argv).risk is Risk.DENY, argv


def test_shell_wrappers_and_interpreters_are_denied():
    cases = [
        ["cmd", "/c", "python", "-m", "pytest", "qa_tests", "-q"],
        ["cmd.exe", "/c", "pip", "install", "x"],
        ["powershell", "-Command", "echo hi"],
        ["pwsh", "-c", "echo hi"],
        ["sh", "-c", "python test.py"],
        ["bash", "-c", "python test.py"],
        ["wsl", "python", "-m", "pytest"],
        ["mshta", "x.hta"],
        ["rundll32", "x.dll,Entry"],
    ]
    for argv in cases:
        assert classify_command(argv).risk is Risk.DENY, argv


def test_inline_code_and_secret_paths_are_denied():
    assert classify_command(["python", "-c", "print(1)"]).risk is Risk.DENY
    assert classify_command(["python", "-m", "pytest", ".env"]).risk is Risk.DENY
    assert classify_command(["python", "--version", ".env"]).risk is Risk.DENY


def test_unknown_or_malformed_commands_are_denied():
    assert classify_command(["node", "-e", "1"]).risk is Risk.DENY
    assert classify_command([]).risk is Risk.DENY
    assert classify_command(["python", "", "x"]).risk is Risk.DENY


def test_child_env_contains_only_the_allowlist():
    source = {
        "PATH": "C:\\bin",
        "SystemRoot": "C:\\Windows",
        "TEMP": "C:\\tmp",
        "OPENAI_API_KEY": "sk-should-not-leak",
        "AITEAM_TOKEN": "token-value",
        "AWS_SECRET_ACCESS_KEY": "aws-value",
        "MY_PASSWORD": "pw-value",
        "HOME": "C:\\Users\\someone",
    }

    child = build_child_env(source)

    assert child["PATH"] == "C:\\bin"
    assert child["SystemRoot"] == "C:\\Windows"
    assert child["PYTHONUTF8"] == "1"
    assert child["PYTHONIOENCODING"] == "utf-8"
    for secret_name in (
        "OPENAI_API_KEY",
        "AITEAM_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "MY_PASSWORD",
    ):
        assert secret_name not in child
    assert "HOME" not in child
    assert "sk-should-not-leak" not in child.values()


def test_gate_denies_when_not_interactive():
    gate = ApprovalGate(approver=lambda prompt: True, interactive=False)

    outcome, reason = gate.request(
        argv=TEST_COMMAND, cwd="c:/project", purpose="run tests"
    )

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "non_interactive_denied"
    assert gate.requested


def test_gate_prompts_once_per_execution():
    prompts: list[str] = []

    def approver(prompt: str) -> bool:
        prompts.append(prompt)
        return True

    gate = ApprovalGate(approver=approver, interactive=True)

    for _ in range(2):
        outcome, reason = gate.request(
            argv=TEST_COMMAND, cwd="c:/project", purpose="run tests"
        )
        assert outcome is ApprovalOutcome.APPROVED
        assert reason is None

    assert len(prompts) == 2
    assert "Command: python -m pytest qa_tests -q" in prompts[0]
    assert "Working directory: c:/project" in prompts[0]
    assert "Approve this execution? [y/N]" in prompts[0]
    assert "no session-wide approval" in prompts[0]


def test_gate_defaults_to_no_on_eof():
    def approver(prompt: str) -> bool:
        raise EOFError

    gate = ApprovalGate(approver=approver, interactive=True)

    outcome, reason = gate.request(
        argv=TEST_COMMAND, cwd="c:/project", purpose="run tests"
    )

    assert outcome is ApprovalOutcome.DENIED
    assert reason == "approval_input_unavailable"


def test_role_tool_sets_are_restricted():
    assert ORCHESTRATOR_TOOLS == ()
    assert "run_command" not in DEVELOPER_TOOLS
    assert "run_command" in QA_TOOLS

    assert "run_command" in forbidden_tools_for(get_role("developer"))
    assert "run_command" in forbidden_tools_for(get_role("orchestrator"))
    assert "run_command" not in forbidden_tools_for(get_role("qa"))
    for shell_name in ("run_shell", "shell", "exec", "cmd", "powershell"):
        assert shell_name in forbidden_tools_for(get_role("qa"))
