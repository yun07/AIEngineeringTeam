"""Engine-level live pricing guard.

The CLI validates live configuration before it resolves a key, but an engine
assembled directly would otherwise accept a zero or invalid price and record
real spend as 0 USD. These tests pin that ``WorkflowEngine.start()`` applies the
same live rules before a run exists, and that fake mode keeps its zero prices.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from aiteam.config import ConfigError
from aiteam.engine.workflow import WorkflowEngine
from aiteam.providers.base import LLMResponse, Usage
from aiteam.providers.fake import FakeProvider
from aiteam.state.store import StateStore
from tests.fakes import (
    SUPPORTED_TEST_MODEL,
    ScriptedRunner,
    StubProvider,
    approving_gate,
    event_kinds,
    json_response,
    make_billing_config,
    make_config,
    plan_payload,
)

MODEL = SUPPORTED_TEST_MODEL
FAKE_MODELS = ("fake-orchestrator", "fake-developer", "fake-qa")


def _engine(tmp_path, config, provider):
    store = StateStore(tmp_path / "repo")
    engine = WorkflowEngine(
        config=config,
        provider=provider,
        store=store,
        project_root=tmp_path / "repo" / "projects" / "demo",
        project_slug="demo",
        approval_gate=approving_gate(),
        command_runner=ScriptedRunner(),
    )
    return engine, store


def _assert_nothing_happened(engine, store, provider) -> None:
    assert provider.calls == []
    assert engine.run is None
    assert engine.sessions == []
    assert store.read_events() == []
    assert list(store.runs_dir.iterdir()) == []
    assert not store.index_path.exists()


@pytest.mark.parametrize(
    "pricing",
    [
        {MODEL: {"input_per_mtok": 0, "output_per_mtok": 1.6}},
        {MODEL: {"input_per_mtok": 0.0, "output_per_mtok": 1.6}},
        {MODEL: {"input_per_mtok": 0.4, "output_per_mtok": 0}},
        {MODEL: {"input_per_mtok": 0.4, "output_per_mtok": 0.0}},
        {MODEL: {"input_per_mtok": -0.4, "output_per_mtok": 1.6}},
        {MODEL: {"input_per_mtok": 0.4, "output_per_mtok": -1.6}},
        {MODEL: {"input_per_mtok": "0.4", "output_per_mtok": 1.6}},
        {MODEL: {"input_per_mtok": 0.4}},
        {},
    ],
    ids=[
        "zero-input",
        "zero-input-float",
        "zero-output",
        "zero-output-float",
        "negative-input",
        "negative-output",
        "non-numeric-input",
        "missing-output-key",
        "missing-model-entry",
    ],
)
def test_direct_engine_rejects_invalid_live_pricing(tmp_path, pricing):
    provider = StubProvider({})
    config = replace(make_billing_config(), pricing=pricing)
    engine, store = _engine(tmp_path, config, provider)

    with pytest.raises(ConfigError):
        engine.start("build a demo project", budget_usd=1.0)

    _assert_nothing_happened(engine, store, provider)


def test_guard_refuses_before_a_budget_is_required(tmp_path):
    # The pricing guard runs first, so an invalid config is reported even when
    # the caller forgot --budget; no run artefact is created either way.
    provider = StubProvider({})
    config = replace(
        make_billing_config(),
        pricing={MODEL: {"input_per_mtok": 0, "output_per_mtok": 1.6}},
    )
    engine, store = _engine(tmp_path, config, provider)

    with pytest.raises(ConfigError):
        engine.start("build a demo project")

    _assert_nothing_happened(engine, store, provider)


def test_fake_mode_engine_still_accepts_zero_prices(tmp_path):
    config = replace(
        make_config(),
        pricing={
            model: {"input_per_mtok": 0.0, "output_per_mtok": 0.0}
            for model in FAKE_MODELS
        },
    )
    provider = FakeProvider(
        by_role={"orchestrator": [json_response(plan_payload(1))]}
    )
    engine, store = _engine(tmp_path, config, provider)

    run = engine.start("build a demo project")
    engine.execute(plan_only=True)

    assert run.budget_usd is None
    assert store.read_usage(run.id) == []
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Fake mode: no billable usage or USD cost." in report


def test_valid_pricing_still_reserves_and_settles(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)), usage=Usage(200, 100)
                )
            ]
        }
    )
    engine, store = _engine(tmp_path, make_billing_config(), provider)

    run = engine.start("build a demo project", budget_usd=1.0)
    engine.execute(plan_only=True)

    kinds = event_kinds(store, run.id)
    assert "budget_reserved" in kinds
    assert "usage_recorded" in kinds
    assert "budget_stopped" not in kinds

    records = store.read_usage(run.id)
    assert len(records) == 1
    assert records[0]["input_tokens"] == 200
    assert records[0]["output_tokens"] == 100
    assert records[0]["usd"] > 0
