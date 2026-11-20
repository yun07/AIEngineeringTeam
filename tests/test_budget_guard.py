"""Budget reservation: preflight, in-flight exposure and hard stops."""

from __future__ import annotations

import json

import pytest

from aiteam.cost.guard import BudgetError, BudgetGuard
from aiteam.cost.manager import CostManager
from aiteam.engine.workflow import WorkflowError
from aiteam.models import RunState
from aiteam.providers.base import ChatMessage, LLMResponse, Usage
from aiteam.state.store import StateStore
from tests.fakes import (
    SUPPORTED_TEST_MODEL,
    StubProvider,
    TEST_PRICING,
    build_billing_engine,
    event_kinds,
    json_response,
    plan_payload,
)

MODEL = SUPPORTED_TEST_MODEL
MESSAGES = [ChatMessage(role="user", content="hello world")]


def make_guard(
    tmp_path,
    budget: float,
    margin: float = 10.0,
    max_context_tokens: int | None = None,
):
    manager = CostManager(
        pricing=TEST_PRICING,
        budget_usd=budget,
        max_output_tokens=1200,
        safety_margin_percent=margin,
        max_context_tokens=max_context_tokens,
    )
    store = StateStore(tmp_path / "repo")
    events: list[tuple[str, dict]] = []
    guard = BudgetGuard(
        manager=manager,
        budget_usd=budget,
        store=store,
        run_id="run-1",
        event_sink=lambda kind, data: events.append((kind, data)),
    )
    return guard, manager, store, events


def test_call_allowed_and_settled_with_actual_usage(tmp_path):
    guard, manager, store, events = make_guard(tmp_path, budget=1.0)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    reservation_id = scope.before_call(system="sys", messages=MESSAGES)
    record = scope.settle_success(reservation_id, Usage(1000, 500))

    assert events[0][0] == "budget_reserved"
    assert record is not None
    assert record.input_tokens == 1000
    assert record.usd == pytest.approx((1000 * 0.4 + 500 * 1.6) / 1_000_000)
    assert store.read_usage("run-1")[0]["input_tokens"] == 1000
    assert manager.spent_usd == pytest.approx(record.usd)
    assert manager.remaining_usd() == pytest.approx(1.0 - record.usd)


def test_preflight_blocks_before_any_call(tmp_path):
    guard, manager, store, events = make_guard(tmp_path, budget=0.0001)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    with pytest.raises(BudgetError) as excinfo:
        scope.before_call(system="sys", messages=MESSAGES)

    assert excinfo.value.reason == "budget_exceeded"
    assert events[0][0] == "budget_stopped"
    assert manager.reserved_total_usd == 0.0
    assert guard.reservations == {}
    assert store.read_usage("run-1") == []


def test_in_flight_reservation_blocks_the_next_call(tmp_path):
    guard, _, _, _ = make_guard(tmp_path, budget=0.003)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    scope.before_call(system="sys", messages=MESSAGES)
    with pytest.raises(BudgetError) as excinfo:
        scope.before_call(system="sys", messages=MESSAGES)

    assert excinfo.value.reason == "budget_exceeded"
    assert guard.in_flight_usd() > 0


def test_next_call_allowed_after_settlement(tmp_path):
    guard, _, _, _ = make_guard(tmp_path, budget=1.0)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    first = scope.before_call(system="sys", messages=MESSAGES)
    scope.settle_success(first, Usage(1000, 500))
    second = scope.before_call(system="sys", messages=MESSAGES)

    assert second
    assert guard.in_flight_usd() > 0


def test_usage_unavailable_keeps_exposure_and_stops_calls(tmp_path):
    guard, manager, store, events = make_guard(tmp_path, budget=1.0)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    reservation_id = scope.before_call(system="sys", messages=MESSAGES)
    with pytest.raises(BudgetError) as excinfo:
        scope.settle_success(reservation_id, None)

    assert excinfo.value.reason == "usage_unavailable"
    assert manager.uncertain_usd > 0
    assert manager.remaining_usd() is None
    assert store.read_usage("run-1") == []
    assert ("usage_unavailable" in [kind for kind, _ in events])

    with pytest.raises(BudgetError) as second:
        scope.before_call(system="sys", messages=MESSAGES)
    assert second.value.reason == "accounting_blocked"


def test_provider_failure_keeps_uncertain_exposure(tmp_path):
    guard, manager, store, events = make_guard(tmp_path, budget=1.0)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    reservation_id = scope.before_call(system="sys", messages=MESSAGES)
    scope.settle_failure(reservation_id, "provider_error")

    assert manager.uncertain_usd > 0
    assert manager.remaining_usd() is None
    assert store.read_usage("run-1") == []
    assert "usage_unavailable" in [kind for kind, _ in events]


def test_overshoot_after_actual_usage_stops_next_call(tmp_path):
    guard, manager, store, events = make_guard(tmp_path, budget=0.05)
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    reservation_id = scope.before_call(system="sys", messages=MESSAGES)
    with pytest.raises(BudgetError) as excinfo:
        scope.settle_success(reservation_id, Usage(100_000, 100_000))

    assert excinfo.value.reason == "budget_overshoot"
    assert manager.overshoot is True
    assert len(store.read_usage("run-1")) == 1
    assert "budget_overshoot" in [kind for kind, _ in events]

    with pytest.raises(BudgetError) as second:
        scope.before_call(system="sys", messages=MESSAGES)
    assert second.value.reason == "accounting_blocked"


def test_context_window_is_checked_before_any_call(tmp_path):
    guard, _, store, events = make_guard(
        tmp_path, budget=1.0, max_context_tokens=10
    )
    scope = guard.scope(task_id="T1", role="developer", model=MODEL)

    with pytest.raises(BudgetError) as excinfo:
        scope.before_call(system="long system prompt", messages=MESSAGES)

    assert excinfo.value.reason == "request_too_large"
    assert guard.reservations == {}
    assert store.read_usage("run-1") == []
    assert "request_rejected" in [kind for kind, _ in events]


def test_engine_stops_after_actual_overshoot(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)),
                    usage=Usage(100_000, 100_000),
                )
            ]
        }
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=0.05)

    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "budget_overshoot" in (result.block_reason or "")
    assert len(provider.calls) == 1
    assert len(store.read_usage(run.id)) == 1
    kinds = event_kinds(store, run.id)
    assert "budget_overshoot" in kinds


def test_engine_preflight_blocks_call_before_provider(tmp_path):
    provider = StubProvider({"orchestrator": [json_response(plan_payload(1))]})
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=0.0001)

    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "budget_exceeded" in (result.block_reason or "")
    assert provider.calls == []
    kinds = event_kinds(store, run.id)
    assert "cost_guard_started" in kinds
    assert "budget_stopped" in kinds
    assert store.read_usage(run.id) == []


def test_engine_records_actual_usage_and_reports_cost(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)),
                    usage=Usage(120, 40),
                )
            ]
        }
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    usage = store.read_usage(run.id)
    assert len(usage) == 1
    expected_usd = (120 * 0.4 + 40 * 1.6) / 1_000_000
    assert usage[0]["usd"] == pytest.approx(expected_usd)
    assert provider.calls[0]["max_output_tokens"] == 1200

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Estimated/Reserved cost (preflight):" in report
    assert f"Actual reported cost: {expected_usd:.6f} USD" in report
    assert "Configured budget: 1.000000 USD" in report
    assert "Accounting uncertainty" in report


def test_engine_requires_a_budget_for_billing_mode(tmp_path):
    engine, _ = build_billing_engine(tmp_path, provider=StubProvider({}))

    with pytest.raises(WorkflowError, match="requires a budget"):
        engine.start("build a demo project")


def test_engine_reports_unknown_remaining_when_usage_is_unavailable(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(text=json.dumps(plan_payload(1)), usage=None)
            ]
        }
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=1.0)

    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "usage_unavailable" in (result.block_reason or "")
    assert store.read_usage(run.id) == []
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Remaining budget: unknown" in report
    assert "Usage unavailable: 1 call(s)" in report


def test_engine_provider_error_keeps_uncertain_exposure(tmp_path):
    provider = StubProvider({}, error=RuntimeError("provider exploded"))
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=1.0)

    result = engine.execute()

    assert result.state is RunState.BLOCKED
    assert "provider_error" in (result.block_reason or "")
    assert store.read_usage(run.id) == []
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Remaining budget: unknown" in report
