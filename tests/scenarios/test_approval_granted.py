"""Approval granted scenario: one approval decision per execution."""

from __future__ import annotations

from aiteam.models import RunState
from aiteam.providers.base import ToolCall
from aiteam.providers.fake import extract_execution_id, json_response
from tests.fakes import (
    DEFAULT_TEST_CONTENT,
    TEST_COMMAND,
    ScriptedRunner,
    approving_gate,
    run_demo,
    tool_response,
)


def _two_run_script():
    verdict = {
        "verdict": "pass",
        "summary": "two runs recorded",
        "checks": [
            {
                "criterion": "C1",
                "name": "positive check",
                "kind": "positive",
                "command": TEST_COMMAND,
                "exit_code": 0,
                "evidence": "1 passed",
                "test_file": "qa_tests/test_demo.py",
            },
            {
                "criterion": "C1",
                "name": "negative check",
                "kind": "negative",
                "command": TEST_COMMAND,
                "exit_code": 0,
                "evidence": "1 passed",
                "test_file": "qa_tests/test_demo.py",
            },
        ],
        "unverified_requirements": [],
    }

    def verdict_response(messages):
        payload = dict(verdict)
        payload["checks"] = [
            {**check, "execution_id": extract_execution_id(messages)}
            for check in verdict["checks"]
        ]
        return json_response(payload)

    return [
        tool_response(
            [
                ToolCall(
                    id="qa_write",
                    name="write_file",
                    arguments={
                        "path": "qa_tests/test_demo.py",
                        "content": DEFAULT_TEST_CONTENT,
                    },
                )
            ]
        ),
        tool_response(
            [
                ToolCall(
                    id="run_1",
                    name="run_command",
                    arguments={"argv": TEST_COMMAND.split()},
                )
            ]
        ),
        tool_response(
            [
                ToolCall(
                    id="run_2",
                    name="run_command",
                    arguments={"argv": TEST_COMMAND.split()},
                )
            ]
        ),
        verdict_response,
    ]


def test_each_execution_requires_its_own_approval(tmp_path):
    gate = approving_gate()
    runner = ScriptedRunner()

    _, store, run, result = run_demo(
        tmp_path,
        qa_script_responses=_two_run_script(),
        gate=gate,
        runner=runner,
    )

    assert result.state is RunState.COMPLETED
    assert len(gate.requested) == 2
    approvals = store.read_approvals(run.id)
    assert len(approvals) == 2
    assert {record["decision"] for record in approvals} == {"approved"}
    assert len(runner.calls) == 2
    assert all(call["argv"] == TEST_COMMAND.split() for call in runner.calls)
