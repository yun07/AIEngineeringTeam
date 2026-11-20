"""Report wording: the cost section matches what the engine now implements.

The old report text claimed that token accounting and USD cost had not arrived
yet. These tests pin the replacement wording for both fake and live modes and
prove the cost figures themselves are unchanged.
"""

from __future__ import annotations

import json

from aiteam.providers.base import LLMResponse, Usage
from tests.fakes import (
    SUPPORTED_TEST_MODEL,
    TEST_PRICING,
    StubProvider,
    build_billing_engine,
    build_engine,
    json_response,
    plan_payload,
)

STALE_CLAIMS = (
    "arrive in M3 and M4",
    "This report contains no cost figures",
)


def _report(store, run_id: str) -> str:
    return (store.run_dir(run_id) / "report.md").read_text(encoding="utf-8")


def _stub_orchestrator(input_tokens: int = 200, output_tokens: int = 100):
    return StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)),
                    usage=Usage(input_tokens, output_tokens),
                )
            ]
        }
    )


def test_fake_mode_report_describes_costs_correctly(tmp_path):
    engine, store = build_engine(
        tmp_path, orchestrator_script=[json_response(plan_payload(1))]
    )
    run = engine.start("build a demo project")

    engine.execute(plan_only=True)

    report = _report(store, run.id)
    assert "## Cost" in report
    assert "Fake mode: no billable usage or USD cost." in report
    assert "## Reporting notes" in report
    for stale in STALE_CLAIMS:
        assert stale not in report


def test_live_report_has_no_stale_m3_m4_wording(tmp_path):
    engine, store = build_billing_engine(
        tmp_path, provider=_stub_orchestrator()
    )
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    report = _report(store, run.id)
    assert "## Reporting notes" in report
    assert "Cost Guard" in report
    for stale in STALE_CLAIMS:
        assert stale not in report


def test_live_report_cost_section_and_figures_are_unchanged(tmp_path):
    engine, store = build_billing_engine(
        tmp_path, provider=_stub_orchestrator(200, 100)
    )
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    prices = TEST_PRICING[SUPPORTED_TEST_MODEL]
    expected_usd = (
        200 * prices["input_per_mtok"] + 100 * prices["output_per_mtok"]
    ) / 1_000_000

    report = _report(store, run.id)
    assert "| Role | Calls | Input tokens | Output tokens | Actual USD |" in report
    assert "| orchestrator | 1 | 200 | 100 |" in report
    assert "Estimated/Reserved cost (preflight):" in report
    assert f"Actual reported cost: {expected_usd:.6f} USD" in report
    assert f"- Configured budget: {1.0:.6f} USD" in report
    assert "Remaining budget:" in report
