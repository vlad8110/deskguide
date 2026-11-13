"""C1 endpoint checks with fictional evidence and isolated internal adapters."""

from dataclasses import asdict, replace
from uuid import UUID

import pytest

from app import create_app
from app.db import get_db
from app.inquiry_types import (
    EvidenceExcerpt,
    EvidenceExpectation,
    EvidencePreparation,
    GenerationResult,
    Passage,
    RetrievalResult,
    SourceRef,
    ValidationResult,
)

QUESTION = "How do I set up the Campus VPN profile?"
ANSWER = "Install the Acme VPN client, sign in, and select the Campus profile."
REF = SourceRef("DOC-003", "s2", "3")


class FictionalServices:
    def __init__(self):
        self.calls = []
        self.retrieved = RetrievalResult(
            (Passage(REF, ANSWER, "VPN Setup Guide", "Installing the client"),),
            "test-index-1",
        )
        self.preparation = "ready"
        self.outbound = "approved"
        self.candidate = GenerationResult(ANSWER, (REF,), "test-adapter-1")
        self.validation = ValidationResult("pass", (REF,))
        self.fail_at = None
        self.hook = lambda stage: None
        self.expected_change = lambda expected: expected

    def record(self, stage, *args, **kwargs):
        self.calls.append((stage, args, kwargs))
        self.hook(stage)
        if self.fail_at == stage:
            raise RuntimeError("private question, credential or provider error")

    def retrieve(self, ctx, question, **kwargs):
        self.record("retrieve", ctx, question, **kwargs)
        return self.retrieved

    def prepare_evidence(self, ctx, inquiry_id, question, retrieved, **kwargs):
        self.record("prepare", ctx, inquiry_id, question, retrieved, **kwargs)
        if self.preparation != "ready":
            return EvidencePreparation(self.preparation)
        expected = EvidenceExpectation(
            inquiry_id,
            "test-policy-1",
            "test-manifest-1",
            "vpn_setup",
            ANSWER,
            (EvidenceExcerpt(REF, 0, len(ANSWER), ANSWER),),
        )
        self.expected = self.expected_change(expected)
        return EvidencePreparation("ready", self.expected)

    def check_outbound(self, ctx, question, retrieved, **kwargs):
        self.record("outbound", ctx, question, retrieved, **kwargs)
        return self.outbound

    def generate(self, generation_request):
        self.record("generate", generation_request)
        return self.candidate

    def validate(self, ctx, inquiry_id, candidate, retrieved, expected, **kwargs):
        self.record(
            "validate", ctx, inquiry_id, candidate, retrieved, expected, **kwargs
        )
        assert expected is self.expected
        assert expected.inquiry_id == inquiry_id
        return self.validation


@pytest.fixture
def services(app):
    adapter = FictionalServices()
    app.extensions["inquiry_services"] = adapter
    return adapter


@pytest.fixture
def ask(client, sign_in):
    sign_in(client)
    token = client.get("/v1/session").json["csrf_token"]

    def submit(payload=None):
        return client.post(
            "/v1/inquiries",
            json=payload
            if payload is not None
            else {
                "requested_operation": "ask_question",
                "question": QUESTION,
            },
            headers={"X-CSRF-Token": token},
        )

    return submit


def assert_no_answer(response, status, reason):
    assert response.status_code == 200
    body = response.json
    assert body["status"] == status
    assert body["suggested_reason"] == reason
    assert body["answer"] is None and body["answer_id"] is None
    assert body["sources"] == [] and body["escalation_offered"] is True


def test_supported_inquiry_runs_ordered_gates_and_returns_versioned_citation(
    app, ask, services, clock
):
    response = ask()
    body = response.json
    assert response.status_code == 200
    assert body["status"] == "answered"
    assert body["answer"] == ANSWER
    assert body["answer_origin"] == "ai_generated" and body["route"] == "ai"
    assert body["escalation_offered"] is False and body["suggested_reason"] is None
    UUID(body["inquiry_id"])
    UUID(body["answer_id"])
    UUID(body["correlation_id"])
    assert body["contract_version"] == "0.3.3"
    assert body["sources"] == [
        {
            "ref": asdict(REF),
            "title": "VPN Setup Guide",
            "section_title": "Installing the client",
            "url": "/v1/sources/DOC-003/sections/s2?version=3",
        }
    ]
    assert [c[0] for c in services.calls] == [
        "retrieve",
        "prepare",
        "outbound",
        "generate",
        "validate",
    ]
    with app.app_context():
        row = get_db().execute("SELECT * FROM inquiries").fetchone()
        assert row["customer_id"] == "c1" and row["outcome"] == "answered"
        assert row["answer_id"] == body["answer_id"]
        assert row["expires_at"] == clock[0] + 30 * 86400


@pytest.fixture
def historical_answer_citation(ask, services, released_sources):
    ref = replace(REF, source_version="2")
    excerpt = "Text v2"
    passage = replace(services.retrieved.passages[0], ref=ref, text=excerpt)
    services.retrieved = replace(services.retrieved, passages=(passage,))
    services.candidate = replace(
        services.candidate, candidate_answer=excerpt, cited_refs=(ref,)
    )
    services.validation = ValidationResult("pass", (ref,))
    services.expected_change = lambda expected: replace(
        expected,
        approved_answer=excerpt,
        required_excerpts=(EvidenceExcerpt(ref, 0, len(excerpt), excerpt),),
    )

    response = ask()
    assert response.status_code == 200
    assert response.json["status"] == "answered"
    assert response.json["answer"] == excerpt
    (citation,) = response.json["sources"]
    assert citation["ref"] == asdict(ref)
    return citation["url"]


def test_answer_citation_opens_historical_version(client, historical_answer_citation):
    assert historical_answer_citation == "/v1/sources/DOC-003/sections/s2?version=2"
    response = client.get(historical_answer_citation)

    assert response.status_code == 200
    assert response.json["ref"] == asdict(replace(REF, source_version="2"))
    assert response.json["text"] == "Text v2"
    assert response.headers["Cache-Control"] == "no-store"


def test_answer_citation_rechecks_access_after_revocation(
    app, client, historical_answer_citation
):
    assert client.get(historical_answer_citation).status_code == 200

    with app.app_context(), get_db() as db:
        db.execute(
            "DELETE FROM document_role_grants WHERE source_id = ? AND role = ?",
            (REF.source_id, "customer"),
        )

    denied = client.get(historical_answer_citation)
    missing = client.get(historical_answer_citation.replace(REF.source_id, "DOC-999"))

    assert denied.status_code == missing.status_code == 404
    denied_error = denied.json["error"]
    missing_error = missing.json["error"]
    denied_error.pop("correlation_id")
    missing_error.pop("correlation_id")
    assert denied_error == missing_error
    assert denied_error["code"] == "NOT_FOUND"
    assert "Text v2" not in denied.get_data(as_text=True)


def test_forged_identity_is_ignored_and_generation_has_only_allowed_fields(
    ask, services
):
    response = ask(
        {
            "requested_operation": "ask_question",
            "question": QUESTION,
            "customer_id": "c2",
            "role": "administrator",
            "approved_context": "forged",
        }
    )
    assert response.status_code == 200
    ctx = services.calls[0][1][0]
    assert ctx.customer_scope == "c1" and ctx.role == "customer"
    generation = next(c[1][0] for c in services.calls if c[0] == "generate")
    payload = asdict(generation)
    assert set(payload) == {
        "question",
        "passages",
        "deadline_ms",
        "configuration_version",
        "correlation_id",
    }
    assert set(payload["passages"][0]) == {"ref", "text", "score", "rank"}
    assert 0 < generation.deadline_ms <= 12000
    assert services.calls[0][2]["deadline_ms"] <= 2000
    with pytest.raises((AttributeError, TypeError)):
        generation.question = "changed"


@pytest.mark.parametrize(
    "preparation,status",
    [
        ("insufficient_evidence", "escalation_offered"),
        ("support_check_unavailable", "temporarily_unavailable"),
        ("unknown", "temporarily_unavailable"),
    ],
)
def test_failed_prechecks_make_zero_generation_calls(
    ask, services, preparation, status
):
    services.preparation = preparation
    reason = (
        "insufficient_evidence"
        if preparation == "insufficient_evidence"
        else "service_unavailable"
    )
    assert_no_answer(ask(), status, reason)
    assert [c[0] for c in services.calls] == ["retrieve", "prepare"]


@pytest.mark.parametrize(
    "ref",
    [
        replace(REF, source_id="DOC-3"),
        replace(REF, section_id="s/2"),
        replace(REF, source_version="0"),
        replace(REF, source_version="9223372036854775808"),
    ],
)
def test_unresolvable_source_reference_stops_before_generation(ask, services, ref):
    passage = replace(services.retrieved.passages[0], ref=ref)
    services.retrieved = replace(services.retrieved, passages=(passage,))
    assert_no_answer(ask(), "temporarily_unavailable", "service_unavailable")
    assert [call[0] for call in services.calls] == ["retrieve"]


@pytest.mark.parametrize(
    "change",
    [
        lambda e: None,
        lambda e: replace(e, inquiry_id="another-inquiry"),
        lambda e: replace(e, manifest_version=""),
        lambda e: replace(e, required_excerpts=()),
        lambda e: replace(e, required_excerpts=(EvidenceExcerpt(REF, -1, 3, "bad"),)),
        lambda e: replace(e, required_excerpts=(EvidenceExcerpt(REF, 0, 3, "bad"),)),
        lambda e: replace(
            e,
            required_excerpts=(
                EvidenceExcerpt(
                    replace(REF, source_version="4"), 0, len(ANSWER), ANSWER
                ),
            ),
        ),
    ],
)
def test_invalid_expectation_cannot_reach_generation(ask, services, change):
    services.expected_change = change
    assert_no_answer(ask(), "temporarily_unavailable", "service_unavailable")
    assert "generate" not in [c[0] for c in services.calls]


@pytest.mark.parametrize(
    "outbound,status,reason",
    [
        ("denied", "escalation_offered", "insufficient_evidence"),
        ("unavailable", "temporarily_unavailable", "service_unavailable"),
        (None, "temporarily_unavailable", "service_unavailable"),
    ],
)
def test_outbound_policy_must_approve_before_generation(
    ask, services, outbound, status, reason
):
    services.outbound = outbound
    assert_no_answer(ask(), status, reason)
    assert "generate" not in [c[0] for c in services.calls]


@pytest.mark.parametrize(
    "candidate",
    [
        GenerationResult("unsupported addition", (REF,), "test"),
        GenerationResult(ANSWER, (), "test"),
        GenerationResult(ANSWER, (replace(REF, source_version="4"),), "test"),
        GenerationResult(ANSWER, (SourceRef("private", "s1", "1"),), "test"),
        GenerationResult(None, (REF,), "test"),
        GenerationResult("x" * 4001, (REF,), "test"),
    ],
)
def test_invalid_candidate_is_suppressed_without_retry(ask, services, candidate):
    services.candidate = candidate
    assert_no_answer(ask(), "escalation_offered", "validation_failed")
    assert [c[0] for c in services.calls].count("generate") == 1


@pytest.mark.parametrize(
    "validation", [ValidationResult("fail"), ValidationResult("pass"), None]
)
def test_validator_must_pass_all_cited_refs(ask, services, validation):
    services.validation = validation
    assert_no_answer(ask(), "escalation_offered", "validation_failed")


@pytest.mark.parametrize(
    "stage,reason,status",
    [
        ("retrieve", "service_unavailable", "temporarily_unavailable"),
        ("prepare", "service_unavailable", "temporarily_unavailable"),
        ("outbound", "service_unavailable", "temporarily_unavailable"),
        ("generate", "provider_failure", "temporarily_unavailable"),
        ("validate", "validation_failed", "escalation_offered"),
    ],
)
def test_dependency_errors_are_safe_and_never_save_support(
    app, ask, services, caplog, stage, reason, status
):
    services.fail_at = stage
    response = ask()
    assert_no_answer(response, status, reason)
    assert "private question" not in response.text + caplog.text
    with app.app_context():
        for table in (
            "support_requests",
            "submission_registrations",
            "submission_receipts",
            "support_replies",
            "feedback",
        ):
            assert get_db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        saved = str(dict(get_db().execute("SELECT * FROM inquiries").fetchone()))
        assert QUESTION not in saved and ANSWER not in saved


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"requested_operation": []},
        {"requested_operation": "other"},
        {"requested_operation": "ask_question"},
        *[
            {"requested_operation": "ask_question", "question": q}
            for q in (None, 3, "", "  ", "x" * 1001, "VPN\n", "\ud800")
        ],
        {"requested_operation": "check_account_status", "question": "VPN"},
    ],
)
def test_invalid_input_never_calls_dependencies(app, ask, services, payload):
    assert ask(payload).status_code == 400
    assert services.calls == []
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM inquiries").fetchone()[0] == 0


def test_conversation_is_not_accepted_without_an_ownership_store(ask, services):
    response = ask(
        {
            "requested_operation": "ask_question",
            "question": QUESTION,
            "conversation_id": "another-customers-id",
        }
    )
    assert response.status_code == 403 and services.calls == []


def test_missing_services_fail_closed(app, ask):
    assert_no_answer(ask(), "temporarily_unavailable", "service_unavailable")


def test_account_status_is_explicit_and_does_not_call_ai(ask, services):
    response = ask({"requested_operation": "check_account_status", "customer_id": "c2"})
    assert_no_answer(response, "escalation_offered", "service_unavailable")
    assert response.json["route"] == "account_status" and services.calls == []


def test_authentication_and_csrf_are_required(client, sign_in, services):
    assert client.post("/v1/inquiries", json={}).status_code == 401
    sign_in(client)
    assert client.post("/v1/inquiries", json={}).json["error"]["code"] == "CSRF_FAILED"
    assert services.calls == []


@pytest.mark.parametrize("username", ["agent-one", "admin-one"])
def test_staff_cannot_use_customer_inquiry_route(client, sign_in, services, username):
    sign_in(client, username)
    token = client.get("/v1/session").json["csrf_token"]
    response = client.post("/v1/inquiries", json={}, headers={"X-CSRF-Token": token})
    assert response.status_code == 403 and services.calls == []


def test_sixth_inquiry_is_rate_limited_and_window_resets(ask, services, clock):
    for _ in range(5):
        assert ask().status_code == 200
    before = len(services.calls)
    response = ask()
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    assert len(services.calls) == before
    clock[0] += 60
    assert ask().status_code == 200


def test_second_active_inquiry_is_denied_by_persisted_admission(app, ask, services):
    nested = []
    services.hook = lambda stage: nested.append(ask()) if stage == "retrieve" else None
    assert ask().status_code == 200
    assert len(nested) == 1 and nested[0].status_code == 429


def test_active_customer_limit_is_shared_by_two_app_instances(
    app, ask, services, sign_in
):
    other = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "TIME_PROVIDER": app.config["TIME_PROVIDER"],
            "SESSION_COOKIE_SECURE": False,
            "SESSION_CLEANUP_N_REQUESTS": None,
        }
    )
    second_services = FictionalServices()
    other.extensions["inquiry_services"] = second_services
    second = other.test_client()
    sign_in(second)
    token = second.get("/v1/session").json["csrf_token"]
    nested = []

    def second_request(stage):
        if stage == "retrieve":
            nested.append(
                second.post(
                    "/v1/inquiries",
                    json={"requested_operation": "ask_question", "question": QUESTION},
                    headers={"X-CSRF-Token": token},
                )
            )

    services.hook = second_request
    assert ask().json["status"] == "answered"
    assert nested[0].status_code == 429 and second_services.calls == []


def test_normalized_question_and_answer_keep_the_approved_meaning(ask, services):
    services.candidate = replace(
        services.candidate, candidate_answer="  " + ANSWER + "  "
    )
    response = ask(
        {"requested_operation": "ask_question", "question": "  " + QUESTION + "  "}
    )
    assert response.json["status"] == "answered"
    assert services.calls[0][1][1] == QUESTION


@pytest.mark.parametrize("stage", ["prepare", "validate"])
def test_no_answer_outcomes_create_only_inquiry_metadata(app, ask, services, stage):
    if stage == "prepare":
        services.preparation = "insufficient_evidence"
    else:
        services.validation = ValidationResult("fail")
    response = ask()
    assert response.json["escalation_offered"] is True
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM inquiries").fetchone()[0] == 1
        for table in (
            "support_requests",
            "submission_registrations",
            "submission_receipts",
        ):
            assert get_db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_empty_permitted_retrieval_is_not_a_retrieval_failure(ask, services):
    services.retrieved = replace(services.retrieved, passages=())
    services.preparation = "insufficient_evidence"
    assert_no_answer(ask(), "escalation_offered", "insufficient_evidence")
    assert [c[0] for c in services.calls] == ["retrieve", "prepare"]


def test_admission_recovers_from_an_abandoned_request(app, ask, services, clock):
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "INSERT INTO inquiries (inquiry_id,customer_id,route,outcome,created_at,expires_at) "
                "VALUES ('abandoned','c1','ai','processing',?,?)",
                (clock[0] - 21, clock[0] + 100),
            )
    assert ask().json["status"] == "answered"


def test_global_admission_is_immediate_and_has_no_dependency_call(app, ask, services):
    app.config["INQUIRY_MAX_ACTIVE"] = 0
    response = ask()
    assert response.status_code == 503
    assert response.json["error"]["code"] == "SERVICE_BUSY"
    assert response.headers["Retry-After"] == "1" and services.calls == []


@pytest.mark.parametrize(
    "stage,elapsed,status,reason",
    [
        ("retrieve", 3, 200, "service_unavailable"),
        ("generate", 13, 200, "provider_failure"),
        ("generate", 19.1, 200, "provider_failure"),
        ("generate", 21, 504, None),
    ],
)
def test_late_results_are_discarded_without_retry(
    app, ask, services, stage, elapsed, status, reason
):
    tick = [0.0]
    app.config["INQUIRY_MONOTONIC"] = lambda: tick[0]

    def advance(current):
        if current == stage:
            tick[0] += elapsed

    services.hook = advance
    response = ask()
    assert response.status_code == status
    if status == 200:
        assert_no_answer(response, "temporarily_unavailable", reason)
    else:
        assert response.json["error"]["code"] == "DEADLINE_EXCEEDED"
    assert [c[0] for c in services.calls].count("generate") <= 1
    with app.app_context():
        assert get_db().execute("SELECT answer_id FROM inquiries").fetchone()[0] is None
        assert (
            get_db().execute("SELECT COUNT(*) FROM support_requests").fetchone()[0] == 0
        )
