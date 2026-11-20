"""usage.jsonl persistence and report totals."""

from __future__ import annotations

import json

import pytest

from aiteam.models import UsageRecord
from aiteam.state.store import StateStore
from aiteam.providers.base import LLMResponse, Usage
from tests.fakes import (
    StubProvider,
    build_billing_engine,
    plan_payload,
)


def test_usage_jsonl_roundtrip_and_filtering(tmp_path):
    store = StateStore(tmp_path / "repo")
    first = UsageRecord(
        ts="t1",
        run_id="run-a",
        task_id="T1",
        role="orchestrator",
        model="gpt-4.1-mini",
        input_tokens=10,
        output_tokens=5,
        usd=0.0001,
    )
    second = UsageRecord(
        ts="t2",
        run_id="run-b",
        task_id="T1",
        role="qa",
        model="gpt-4.1-mini",
        input_tokens=20,
        output_tokens=10,
        usd=0.0002,
    )

    store.append_usage(first)
    store.append_usage(second)

    assert len(store.read_usage()) == 2
    assert store.read_usage("run-a")[0]["role"] == "orchestrator"
    assert store.read_usage("run-b")[0]["usd"] == pytest.approx(0.0002)


def test_engine_usage_matches_report_total(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)),
                    usage=Usage(200, 100),
                )
            ]
        }
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    records = store.read_usage(run.id)
    assert len(records) == 1
    record = records[0]
    assert record["run_id"] == run.id
    assert record["task_id"] == "plan"
    assert record["role"] == "orchestrator"
    assert record["model"] == "gpt-4.1-mini"
    assert record["input_tokens"] == 200
    assert record["output_tokens"] == 100

    total = sum(item["usd"] for item in records)
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert f"Actual reported cost: {total:.6f} USD" in report
    assert f"{total:.6f}" in report
