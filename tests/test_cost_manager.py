"""Pricing, reserved cost, actual USD and usage validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aiteam.cost.manager import (
    CostError,
    CostManager,
    RequestTooLarge,
    UsageUnavailable,
)
from aiteam.models import UsageRecord
from aiteam.providers.base import ChatMessage, Usage
from tests.fakes import SUPPORTED_TEST_MODEL, TEST_PRICING

MODEL = SUPPORTED_TEST_MODEL


def make_manager(
    *,
    budget: float | None = 1.0,
    margin: float = 10.0,
    max_context_tokens: int | None = None,
) -> CostManager:
    return CostManager(
        pricing=TEST_PRICING,
        budget_usd=budget,
        max_output_tokens=1200,
        safety_margin_percent=margin,
        max_context_tokens=max_context_tokens,
    )


def test_unknown_model_has_no_price():
    with pytest.raises(CostError, match="no pricing entry"):
        make_manager().prices_for("unknown-model")


def test_estimate_reserves_input_plus_max_output_with_margin():
    manager = make_manager(margin=10.0)
    estimate = manager.estimate(
        model=MODEL,
        system="system",
        messages=[ChatMessage(role="user", content="hello world")],
        tools=[],
    )

    price_in, price_out = 0.4, 1.6
    expected = (
        estimate.estimated_input_tokens * price_in + 1200 * price_out
    ) / 1_000_000 * 1.10

    assert estimate.max_output_tokens == 1200
    assert estimate.estimated_input_tokens > 0
    assert estimate.reserved_usd == round(expected, 6)


def test_estimate_rejects_requests_over_the_context_window():
    manager = make_manager(max_context_tokens=10)

    with pytest.raises(RequestTooLarge, match="request_too_large"):
        manager.estimate(
            model=MODEL,
            system="a long enough system prompt",
            messages=[ChatMessage(role="user", content="hello world")],
            tools=[],
        )


def test_actual_usd_matches_pricing_table():
    assert make_manager().actual_usd(MODEL, 1000, 500) == round(
        (1000 * 0.4 + 500 * 1.6) / 1_000_000, 6
    )


def test_records_update_totals_and_per_role():
    manager = make_manager()
    developer = UsageRecord(
        ts="t1",
        run_id="run",
        task_id="T1",
        role="developer",
        model=MODEL,
        input_tokens=1000,
        output_tokens=500,
        usd=0.0012,
    )
    qa = UsageRecord(
        ts="t2",
        run_id="run",
        task_id="T1",
        role="qa",
        model=MODEL,
        input_tokens=2000,
        output_tokens=1000,
        usd=0.0024,
    )

    manager.record(developer)
    manager.record(qa)

    assert manager.spent_usd == pytest.approx(0.0036)
    assert manager.by_role["developer"].calls == 1
    assert manager.by_role["qa"].input_tokens == 2000
    assert manager.remaining_usd() == pytest.approx(0.9964)


@pytest.mark.parametrize(
    "bad_usage",
    [
        None,
        Usage(0, 0),
        Usage(-1, 10),
        SimpleNamespace(input_tokens="10", output_tokens=5),
        SimpleNamespace(input_tokens=True, output_tokens=5),
    ],
)
def test_unusable_usage_is_rejected(bad_usage):
    with pytest.raises(UsageUnavailable):
        make_manager().validate_usage(bad_usage)


def test_remaining_is_unknown_after_uncertainty():
    manager = make_manager()
    manager.mark_uncertain(0.01)

    assert manager.remaining_usd() is None
    assert manager.uncertain_usd == pytest.approx(0.01)
    assert "unknown" in manager.uncertainty_note().lower()


def test_overshoot_flag_is_set_when_actual_exceeds_budget():
    manager = make_manager(budget=0.0001)
    manager.record(
        UsageRecord(
            ts="t",
            run_id="run",
            task_id="T1",
            role="developer",
            model=MODEL,
            input_tokens=1000,
            output_tokens=500,
            usd=0.01,
        )
    )

    assert manager.overshoot is True
