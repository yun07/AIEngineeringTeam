"""Fake mode must never produce billable usage or USD cost."""

from __future__ import annotations

from aiteam.models import RunState
from tests.fakes import (
    build_engine,
    event_kinds,
    json_response,
    plan_payload,
    qa_script,
    run_demo,
)


def test_fake_run_has_no_billable_usage(tmp_path):
    engine, store, run, result = run_demo(
        tmp_path, qa_script_responses=qa_script()
    )

    assert result.state is RunState.COMPLETED
    assert engine._cost_manager is None
    assert store.read_usage(run.id) == []
    assert "cost_guard_started" not in event_kinds(store, run.id)

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Fake mode: no billable usage or USD cost." in report
    assert "Actual reported cost" not in report
    assert "Configured budget" not in report


def test_fake_start_does_not_require_a_budget(tmp_path):
    engine, _ = build_engine(
        tmp_path,
        orchestrator_script=[json_response(plan_payload(1))],
        developer_script=[],
        qa_script_responses=[],
    )

    run = engine.start("build a demo project")

    assert run.budget_usd is None
    assert engine._budget_guard is None
