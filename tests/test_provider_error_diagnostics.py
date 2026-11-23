"""Bounded, redacted provider diagnostics for HTTP status errors.

Everything here is mocked: a fake client raises SDK-shaped exceptions, so no
network access occurs and no real key is ever used.
"""

from __future__ import annotations

import json

import pytest

from aiteam.engine.workflow import WorkflowEngine
from aiteam.providers.base import ChatMessage
from aiteam.providers.openai_provider import (
    DETAIL_TEXT_LIMIT,
    OpenAIProvider,
    ProviderError,
)
from aiteam.secrets import SecretBoundary
from aiteam.state.store import StateStore
from tests.fakes import StubProvider, approving_gate, make_billing_config
from tests.test_openai_provider import FakeClient

KEY = "sk-dummy-diagnostics-not-a-real-key"
MESSAGES = [ChatMessage(role="user", content="hi")]


class APIStatusError(Exception):
    """Minimal stand-in for ``openai.APIStatusError`` (3.57.0 shape)."""

    def __init__(self, message, *, status_code=400, request_id=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.body = body


class AuthenticationError(APIStatusError):
    def __init__(self, message, **kwargs):
        kwargs.setdefault("status_code", 401)
        super().__init__(message, **kwargs)


class RateLimitError(APIStatusError):
    def __init__(self, message, **kwargs):
        kwargs.setdefault("status_code", 429)
        super().__init__(message, **kwargs)


class ExplodingBody(dict):
    """Body whose access fails, to exercise the fallback path."""

    def get(self, key, default=None):
        raise RuntimeError("body access failed")


def _provider(error):
    client = FakeClient(None, error)
    return OpenAIProvider(client, secret_boundary=SecretBoundary([KEY]))


def _raise(error) -> ProviderError:
    provider = _provider(error)
    with pytest.raises(ProviderError) as excinfo:
        provider.complete(
            model="gpt-4.1-mini",
            system="sys",
            messages=MESSAGES,
            tools=[],
            max_output_tokens=16,
        )
    return excinfo.value


# --- 1. structured fields ---------------------------------------------------


def test_http_400_structured_fields_are_captured():
    error = APIStatusError(
        "Error code: 400",
        status_code=400,
        request_id="req_abc123",
        body={
            "error": {
                "message": "invalid request",
                "type": "invalid_request_error",
                "code": "invalid_param",
            }
        },
    )

    raised = _raise(error)

    assert raised.kind == "api_status_400"
    assert raised.status_code == 400
    assert raised.provider_details == {
        "status_code": 400,
        "request_id": "req_abc123",
        "error_type": "invalid_request_error",
        "error_code": "invalid_param",
        "error_message": "invalid request",
    }


def test_top_level_error_fields_are_captured_when_there_is_no_error_object():
    error = APIStatusError(
        "Error code: 400",
        body={"message": "bad payload", "type": "invalid_request_error"},
    )

    raised = _raise(error)

    assert raised.provider_details["error_message"] == "bad payload"
    assert raised.provider_details["error_type"] == "invalid_request_error"
    assert "error_code" not in raised.provider_details


# --- 2. classification unchanged -------------------------------------------


@pytest.mark.parametrize(
    ("error_factory", "kind", "status_code"),
    [
        (AuthenticationError, "authentication", 401),
        (RateLimitError, "rate_limit", 429),
    ],
)
def test_auth_and_rate_limit_classification_is_unchanged(
    error_factory, kind, status_code
):
    raised = _raise(error_factory("Error code: %d" % status_code))

    assert raised.kind == kind
    assert raised.status_code == status_code
    assert raised.provider_details["status_code"] == status_code


# --- 3-5. missing or malformed data ---------------------------------------


def test_missing_request_id_is_omitted():
    raised = _raise(APIStatusError("Error code: 400", body={"error": {}}))

    assert "request_id" not in raised.provider_details
    assert raised.provider_details == {"status_code": 400}


@pytest.mark.parametrize(
    "body",
    [None, "not-json", b"\x00binary", {"unexpected": 1}, ["list", "body"]],
    ids=["none", "string", "bytes", "no-error-key", "list"],
)
def test_missing_or_malformed_body_keeps_only_the_status_code(body):
    raised = _raise(APIStatusError("Error code: 400", body=body))

    assert raised.provider_details == {"status_code": 400}
    assert str(raised) == "Error code: 400"


def test_missing_structured_error_fields_are_skipped():
    error = APIStatusError(
        "Error code: 400",
        body={"error": {"message": None, "type": 12, "code": True}},
    )

    raised = _raise(error)

    # bool / None are not accepted as diagnostic text; ints are stringified.
    assert raised.provider_details == {"status_code": 400, "error_type": "12"}


# --- 6. secret redaction in every persisted field --------------------------


def test_secret_is_redacted_in_every_diagnostic_field():
    error = APIStatusError(
        f"Error code: 400 - {KEY}",
        status_code=400,
        request_id=f"req_{KEY}",
        body={
            "error": {
                "message": f"bad key {KEY}",
                "type": f"type_{KEY}",
                "code": f"code_{KEY}",
            }
        },
    )

    raised = _raise(error)

    serialized = json.dumps(raised.provider_details)
    assert KEY not in serialized
    assert KEY not in str(raised)
    assert "[REDACTED]" in raised.provider_details["request_id"]
    assert "[REDACTED]" in raised.provider_details["error_message"]
    assert "[REDACTED]" in raised.provider_details["error_type"]
    assert "[REDACTED]" in raised.provider_details["error_code"]


# --- 7. fallback when extraction fails ------------------------------------


def test_extraction_failure_falls_back_to_the_generic_message():
    error = APIStatusError(
        "Error code: 400", request_id="req_1", body=ExplodingBody()
    )

    raised = _raise(error)

    assert raised.provider_details == {"status_code": 400}
    assert str(raised) == "Error code: 400"
    assert raised.kind == "api_status_400"


# --- 8. bounded text -------------------------------------------------------


def test_provider_message_is_length_bounded():
    error = APIStatusError(
        "Error code: 400",
        body={"error": {"message": "x" * 5000}},
    )

    raised = _raise(error)

    message = raised.provider_details["error_message"]
    assert len(message) == DETAIL_TEXT_LIMIT + 3
    assert message.endswith("...")


# --- 9-10. workflow persistence and fail-closed cost accounting -----------


def _billing_engine(tmp_path, provider, boundary):
    store = StateStore(tmp_path / "repo")
    engine = WorkflowEngine(
        config=make_billing_config(),
        provider=provider,
        store=store,
        project_root=tmp_path / "repo" / "projects" / "demo",
        project_slug="demo",
        approval_gate=approving_gate(),
        secret_boundary=boundary,
    )
    return engine, store


def test_workflow_event_carries_redacted_details_and_no_secret_is_persisted(
    tmp_path,
):
    boundary = SecretBoundary([KEY])
    provider = StubProvider(
        {},
        error=ProviderError(
            "api_status_400",
            f"Error code: 400 - {KEY}",
            status_code=400,
            provider_details={
                "status_code": 400,
                "request_id": f"req_{KEY}",
                "error_message": f"leaked {KEY}",
            },
        ),
    )
    engine, store = _billing_engine(tmp_path, provider, boundary)
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    events = [e for e in store.read_events(run.id) if e["kind"] == "provider_error"]
    assert len(events) == 1
    details = events[0]["data"]["provider_details"]
    assert details["status_code"] == 400
    assert KEY not in json.dumps(details)
    assert "[REDACTED]" in details["error_message"]

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "provider_error" in report
    assert KEY not in report

    # Nothing anywhere in the run tree may contain the dummy key.
    for path in (tmp_path / "repo").rglob("*"):
        if path.is_file():
            assert KEY not in path.read_text(encoding="utf-8")


def test_missing_usage_stays_uncertain_after_a_provider_error(tmp_path):
    boundary = SecretBoundary([KEY])
    provider = StubProvider(
        {}, error=ProviderError("api_status_400", "Error code: 400", status_code=400)
    )
    engine, store = _billing_engine(tmp_path, provider, boundary)
    run = engine.start("build a demo project", budget_usd=1.0)

    engine.execute(plan_only=True)

    assert store.read_usage(run.id) == []
    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    assert "Actual reported cost: 0.000000 USD" in report
    assert "Remaining budget: unknown" in report
    assert "Usage unavailable: 1 call(s)" in report
