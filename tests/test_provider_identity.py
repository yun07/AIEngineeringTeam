"""Provider identity consistency: fake and non-fake must not be mixed.

A fake config paired with a billable adapter would skip live validation, the
budget requirement and the Cost Guard. A live config paired with the fake
adapter would record synthetic usage as real cost against a mislabelled
provider. The engine therefore classifies both sides as fake or non-fake and
refuses a mismatch before any workspace, run or event exists.
"""

from __future__ import annotations

import json

import pytest

from aiteam.engine.workflow import WorkflowEngine, WorkflowError
from aiteam.models import RunState
from aiteam.providers.base import LLMResponse, Usage
from aiteam.providers.fake import FakeProvider
from aiteam.providers.openai_provider import OpenAIProvider
from aiteam.secrets import SecretBoundary
from aiteam.state.store import StateStore
from tests.fakes import (
    ScriptedRunner,
    StubProvider,
    approving_gate,
    build_billing_engine,
    event_kinds,
    json_response,
    make_billing_config,
    make_config,
    plan_payload,
    qa_script,
    run_demo,
)

# An inert SDK client: the adapter never sees a request in these tests.
INERT_CLIENT = object()


class _NoNameProvider:
    """Runtime provider with no ``name`` attribute at all."""

    def complete(self, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("a nameless provider must never be called")


class _EmptyNameProvider:
    name = ""

    def complete(self, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("an empty-name provider must never be called")


class _BlankNameProvider:
    name = "   "

    def complete(self, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("a blank-name provider must never be called")


class _NonStringNameProvider:
    name = 123

    def complete(self, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("a non-string-name provider must never be called")


def _openai_provider() -> OpenAIProvider:
    return OpenAIProvider(
        INERT_CLIENT, secret_boundary=SecretBoundary("dummy-key-not-real")
    )


def _engine_kwargs(tmp_path, config, provider, store):
    return {
        "config": config,
        "provider": provider,
        "store": store,
        "project_root": tmp_path / "repo" / "projects" / "demo",
        "project_slug": "demo",
        "approval_gate": approving_gate(),
        "command_runner": ScriptedRunner(),
    }


def _reject(tmp_path, config, provider):
    store = StateStore(tmp_path / "repo")
    with pytest.raises(WorkflowError):
        WorkflowEngine(**_engine_kwargs(tmp_path, config, provider, store))
    return store


def _assert_nothing_created(tmp_path, store) -> None:
    assert store.read_events() == []
    assert list(store.runs_dir.iterdir()) == []
    assert not store.index_path.exists()
    # Workspace creation happens after the identity check, so the project
    # directory must not exist either.
    assert not (tmp_path / "repo" / "projects").exists()


# --- Accepted pairings -----------------------------------------------------


def test_fake_config_with_fake_provider_is_accepted(tmp_path):
    engine, store, run, result = run_demo(
        tmp_path, qa_script_responses=qa_script()
    )

    assert result.state is RunState.COMPLETED
    assert engine._provider.name == "fake"
    assert engine._cost_manager is None
    assert store.read_usage(run.id) == []


def test_live_config_with_openai_provider_is_accepted(tmp_path):
    store = StateStore(tmp_path / "repo")
    provider = _openai_provider()

    engine = WorkflowEngine(
        **_engine_kwargs(tmp_path, make_billing_config(), provider, store)
    )

    assert engine._provider.name == "openai"
    assert engine._cost_manager is None

    run = engine.start("build a demo project", budget_usd=1.0)

    # The live branch is active even though no request is made here.
    assert run.provider == "openai"
    assert engine._cost_manager is not None
    assert "cost_guard_started" in event_kinds(store, run.id)


def test_live_config_with_stub_provider_is_accepted_and_bills(tmp_path):
    provider = StubProvider(
        {
            "orchestrator": [
                LLMResponse(
                    text=json.dumps(plan_payload(1)), usage=Usage(200, 100)
                )
            ]
        }
    )
    engine, store = build_billing_engine(tmp_path, provider=provider)

    run = engine.start("build a demo project", budget_usd=1.0)
    engine.execute(plan_only=True)

    kinds = event_kinds(store, run.id)
    assert "budget_reserved" in kinds
    assert "usage_recorded" in kinds
    assert "budget_stopped" not in kinds

    records = store.read_usage(run.id)
    assert len(records) == 1
    assert records[0]["input_tokens"] == 200
    assert records[0]["usd"] > 0


# --- Rejected pairings -----------------------------------------------------


def test_fake_config_with_openai_provider_is_rejected(tmp_path):
    store = _reject(tmp_path, make_config(), _openai_provider())

    _assert_nothing_created(tmp_path, store)


def test_fake_config_with_stub_provider_is_rejected(tmp_path):
    provider = StubProvider({})

    store = _reject(tmp_path, make_config(), provider)

    assert provider.calls == []
    _assert_nothing_created(tmp_path, store)


def test_live_config_with_fake_provider_is_rejected(tmp_path):
    provider = FakeProvider(
        by_role={"orchestrator": [json_response(plan_payload(1))]}
    )

    store = _reject(tmp_path, make_billing_config(), provider)

    _assert_nothing_created(tmp_path, store)
    assert store.read_usage() == []


# --- Unidentifiable providers fail closed ---------------------------------


@pytest.mark.parametrize(
    "provider",
    [
        _NoNameProvider(),
        _EmptyNameProvider(),
        _BlankNameProvider(),
        _NonStringNameProvider(),
    ],
    ids=["missing-name", "empty-name", "blank-name", "non-string-name"],
)
@pytest.mark.parametrize("config_kind", ["fake", "live"], ids=["fake-config", "live-config"])
def test_invalid_provider_name_is_rejected(tmp_path, provider, config_kind):
    config = make_config() if config_kind == "fake" else make_billing_config()

    store = _reject(tmp_path, config, provider)

    _assert_nothing_created(tmp_path, store)


def test_invalid_provider_name_error_message_is_safe_and_explicit(tmp_path):
    store = StateStore(tmp_path / "repo")

    with pytest.raises(WorkflowError) as excinfo:
        WorkflowEngine(
            **_engine_kwargs(tmp_path, make_config(), _NoNameProvider(), store)
        )

    message = str(excinfo.value)
    assert "provider identity" in message
    assert "sk-" not in message
    _assert_nothing_created(tmp_path, store)
