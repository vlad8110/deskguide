"""C4 confirmation, scoped retries, commit recovery and concurrent state checks."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from app import create_app, support
from app.db import get_db


@pytest.fixture
def customer(client, sign_in):
    sign_in(client)
    return client, {"X-CSRF-Token": client.get("/v1/session").json["csrf_token"]}


def post(api, path, body):
    client, headers = api
    return client.post(path, json=body, headers=headers)


def register(api):
    return post(api, "/v1/escalations/submission-ids", {"operation": "escalation"})


def payload(submission_id, **extra):
    return dict(
        submission_id=submission_id,
        reason="human_requested",
        content="The fictional VPN profile is missing.",
        note="Tried the documented steps.",
        consent_to_share=True,
        **extra,
    )


def submit(api):
    registration = register(api)
    assert registration.status_code == 201
    body = payload(registration.json["submission_id"])
    return body, post(api, "/v1/escalations", body)


def counts(app):
    with app.app_context():
        return {
            name: get_db().execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in (
                "submission_registrations",
                "support_requests",
                "submission_receipts",
                "support_replies",
            )
        }


@pytest.fixture
def waiting(app, customer):
    original, response = submit(customer)
    assert response.status_code == 201
    rid = response.json["request_id"]
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET state='waiting_for_customer',assigned_agent_id='a1',version=4 WHERE request_id=?",
                (rid,),
            )
    return rid, original


def reply_registration(api, rid):
    return post(api, f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"})


def test_registration_is_not_a_support_save(app, customer, clock):
    response = register(customer)
    assert response.status_code == 201
    body = response.json
    assert body["registration_state"] == "unused" and body["operation"] == "escalation"
    state = customer[0].get("/v1/escalations/" + body["submission_id"]).json
    assert state["saved"] is False and state["request_id"] is None
    assert state["version"] is None
    assert state["expires_at"] == body["expires_at"]
    assert counts(app)["support_requests"] == counts(app)["submission_receipts"] == 0
    with app.app_context():
        row = get_db().execute("SELECT * FROM submission_registrations").fetchone()
        assert row["registered_at"] == clock[0] and row["expires_at"] == clock[0] + 1800


def test_confirmed_save_is_atomic_and_acknowledged_after_commit(app, customer):
    body, response = submit(customer)
    assert response.status_code == 201
    saved = response.json
    assert (
        saved["state"] == "queued"
        and saved["acknowledgement"] == "Your request has been saved."
    )
    # Independent connection sees the record before the acknowledgement is inspected.
    connection = sqlite3.connect(app.config["DATABASE"])
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM support_requests").fetchone()[0]
            == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM submission_receipts").fetchone()[0]
            == 1
        )
        row = connection.execute(
            "SELECT customer_id,content,note FROM support_requests"
        ).fetchone()
        assert row == ("c1", body["content"], body["note"])
        digest = connection.execute(
            "SELECT payload_fingerprint FROM submission_receipts"
        ).fetchone()[0]
        assert (
            digest.startswith("sha256:")
            and body["content"] not in digest
            and body["note"] not in digest
        )
    finally:
        connection.close()
    state = customer[0].get("/v1/escalations/" + body["submission_id"]).json
    assert state["saved"] is True and state["request_id"] == saved["request_id"]
    assert state["expires_at"] is None


def test_same_id_same_payload_replays_without_duplication(app, customer):
    body, first = submit(customer)
    replay = post(customer, "/v1/escalations", body)
    assert replay.status_code == 200
    for field in ("request_id", "submission_id", "state", "created_at"):
        assert replay.json[field] == first.json[field]
    assert counts(app) == dict(
        submission_registrations=1,
        support_requests=1,
        submission_receipts=1,
        support_replies=0,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("content", "different"),
        ("note", "different note"),
        ("reason", "action_required"),
        ("inquiry_id", str(uuid4())),
    ],
)
def test_changed_payload_conflicts_even_if_a_field_is_not_rechecked(
    app, customer, field, value
):
    body, _ = submit(customer)
    response = post(customer, "/v1/escalations", {**body, field: value})
    assert response.status_code == 409 and response.json["error"]["code"] == "CONFLICT"
    assert counts(app)["support_requests"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("consent_to_share", False),
        ("consent_to_share", 1),
        ("consent_to_share", "true"),
        ("content", ""),
        ("content", "x" * 1001),
        ("content", "bad\x00text"),
        ("note", "x" * 2001),
        ("note", []),
        ("reason", "invalid"),
        ("reason", []),
        ("submission_id", "unregistered"),
        ("inquiry_id", "invalid"),
        ("customer_id", "c2"),
    ],
)
def test_invalid_or_unconfirmed_submission_creates_no_request(
    app, customer, field, value
):
    sid = register(customer).json["submission_id"]
    body = {**payload(sid), field: value}
    response = post(customer, "/v1/escalations", body)
    assert response.status_code == 400
    assert counts(app)["support_requests"] == counts(app)["submission_receipts"] == 0
    assert (
        customer[0].get("/v1/escalations/" + sid).json["registration_state"] == "unused"
    )


def test_optional_note_is_not_required_and_multiline_reviewed_text_is_allowed(
    app, customer
):
    sid = register(customer).json["submission_id"]
    body = payload(sid)
    del body["note"]
    body["content"] = "Reviewed first line.\nReviewed second line."
    assert post(customer, "/v1/escalations", body).status_code == 201
    with app.app_context():
        assert (
            get_db().execute("SELECT note FROM support_requests").fetchone()[0] is None
        )


def test_foreign_and_unknown_submission_ids_are_indistinguishable(
    app, customer, sign_in
):
    sid = register(customer).json["submission_id"]
    other = app.test_client()
    sign_in(other, "customer-two")
    api = other, {"X-CSRF-Token": other.get("/v1/session").json["csrf_token"]}
    for method in ("status", "submit"):
        results = []
        for key in (sid, str(uuid4())):
            response = (
                other.get("/v1/escalations/" + key)
                if method == "status"
                else post(api, "/v1/escalations", payload(key))
            )
            assert response.status_code == 404
            results.append(response.json["error"]["message"])
        assert results[0] == results[1]
    assert counts(app)["support_requests"] == 0


def test_foreign_and_expired_inquiries_are_denied_without_consuming_id(
    app, customer, clock
):
    inquiry = str(uuid4())
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "INSERT INTO inquiries (inquiry_id,customer_id,route,created_at,expires_at) VALUES (?,'c2','ai',?,?)",
                (inquiry, clock[0], clock[0] + 60),
            )
    sid = register(customer).json["submission_id"]
    response = post(customer, "/v1/escalations", payload(sid, inquiry_id=inquiry))
    assert response.status_code == 403
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE inquiries SET customer_id='c1',created_at=created_at-1,expires_at=? WHERE inquiry_id=?",
                (clock[0], inquiry),
            )
    assert (
        post(customer, "/v1/escalations", payload(sid, inquiry_id=inquiry)).status_code
        == 403
    )
    assert counts(app)["support_requests"] == 0


def test_own_inquiry_links_without_copying_its_history(app, customer):
    token = customer[1]
    inquiry = (
        customer[0]
        .post(
            "/v1/inquiries",
            json={
                "requested_operation": "ask_question",
                "question": "Private fictional question",
            },
            headers=token,
        )
        .json["inquiry_id"]
    )
    sid = register(customer).json["submission_id"]
    body = payload(sid, inquiry_id=inquiry)
    assert post(customer, "/v1/escalations", body).status_code == 201
    with app.app_context():
        row = get_db().execute("SELECT * FROM support_requests").fetchone()
        assert row["inquiry_id"] == inquiry and "Private fictional question" not in str(
            dict(row)
        )


def test_three_pending_id_limit_is_combined_and_does_not_evict(app, customer, waiting):
    rid, _ = waiting
    first = register(customer).json["submission_id"]
    second = reply_registration(customer, rid).json["submission_id"]
    third = register(customer).json["submission_id"]
    response = reply_registration(customer, rid)
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    for sid in (first, second, third):
        assert (
            customer[0].get("/v1/escalations/" + sid).json["registration_state"]
            == "unused"
        )


def expire_unused(clock, client):
    clock[0] += 1700
    assert client.get("/v1/session").status_code == 200
    clock[0] += 100


def test_expired_unused_id_is_rejected_and_does_not_count_toward_cap(
    app, customer, clock
):
    ids = [register(customer).json["submission_id"] for _ in range(3)]
    expire_unused(clock, customer[0])
    sid = ids[0]
    assert (
        customer[0].get("/v1/escalations/" + sid).json["registration_state"]
        == "expired"
    )
    assert post(customer, "/v1/escalations", payload(sid)).status_code == 410
    assert register(customer).status_code == 201
    assert counts(app)["support_requests"] == 0


def test_completed_receipt_survives_unused_expiry_and_cleanup(app, customer, clock):
    body, first = submit(customer)
    expire_unused(clock, customer[0])
    assert app.test_cli_runner().invoke(args=["cleanup-support"]).exit_code == 0
    replay = post(customer, "/v1/escalations", body)
    assert (
        replay.status_code == 200
        and replay.json["request_id"] == first.json["request_id"]
    )


def test_request_rate_limit_counts_new_saves_but_not_replays(customer, clock):
    original = None
    for _ in range(5):
        body, response = submit(customer)
        assert response.status_code == 201
        original = body
    assert post(customer, "/v1/escalations", original).status_code == 200
    sid = register(customer).json["submission_id"]
    assert post(customer, "/v1/escalations", payload(sid)).status_code == 429


def test_support_capacity_is_separate_from_ai_and_replays_remain_available(
    app, customer
):
    app.config["INQUIRY_MAX_ACTIVE"] = 0
    body, first = submit(customer)
    assert first.status_code == 201
    app.config["SUPPORT_MAX_OPEN_REQUESTS"] = 0
    assert register(customer).status_code == 503
    assert post(customer, "/v1/escalations", body).status_code == 200


@pytest.mark.parametrize("username", ["agent-one", "admin-one"])
def test_staff_cannot_call_customer_support_routes(app, sign_in, username):
    client = app.test_client()
    sign_in(client, username)
    api = client, {"X-CSRF-Token": client.get("/v1/session").json["csrf_token"]}
    sid, rid = str(uuid4()), str(uuid4())
    for path, body in [
        ("/v1/escalations/submission-ids", {"operation": "escalation"}),
        ("/v1/escalations", payload(sid)),
        (f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}),
        (
            f"/v1/escalations/{rid}/replies",
            {"submission_id": sid, "message": "test", "expected_version": 1},
        ),
    ]:
        assert post(api, path, body).status_code == 403
    assert client.get("/v1/escalations/" + sid).status_code == 403


def test_anonymous_and_missing_csrf_requests_are_denied(client, sign_in):
    assert register((client, {})).status_code == 401
    sign_in(client)
    assert register((client, {})).json["error"]["code"] == "CSRF_FAILED"


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {"operation": "reply"},
        {"operation": "escalation", "customer_id": "c2"},
    ],
)
def test_registration_rejects_invalid_body_without_creating_anything(
    app, customer, body
):
    response = post(customer, "/v1/escalations/submission-ids", body)
    assert response.status_code == 400 and counts(app)["submission_registrations"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("message", ""),
        ("message", "x" * 2001),
        ("expected_version", True),
        ("expected_version", 0),
        ("expected_version", "4"),
    ],
)
def test_reply_validation_never_consumes_the_id(app, customer, waiting, field, value):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    body = {
        "submission_id": sid,
        "message": "Reviewed reply",
        "expected_version": 4,
        field: value,
    }
    assert post(customer, f"/v1/escalations/{rid}/replies", body).status_code == 400
    assert counts(app)["support_replies"] == 0
    assert (
        customer[0].get("/v1/escalations/" + sid).json["registration_state"] == "unused"
    )


def test_reply_parent_and_completed_receipt_are_private(
    app, customer, waiting, sign_in
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    second = app.test_client()
    sign_in(second, "customer-two")
    other = second, {"X-CSRF-Token": second.get("/v1/session").json["csrf_token"]}
    assert reply_registration(other, rid).status_code == 404
    assert (
        post(
            other,
            f"/v1/escalations/{rid}/replies",
            dict(submission_id=sid, message="Foreign reply", expected_version=4),
        ).status_code
        == 404
    )
    assert second.get("/v1/escalations/" + sid).status_code == 404
    assert counts(app)["support_replies"] == 0


def test_reply_changes_state_once_and_retains_agent(app, customer, waiting):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    body = dict(
        submission_id=sid, message="Reviewed customer reply.", expected_version=4
    )
    first = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert (
        first.status_code == 201
        and first.json["state"] == "in_review"
        and first.json["version"] == 5
    )
    replay = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert (
        replay.status_code == 200 and replay.json["reply_id"] == first.json["reply_id"]
    )
    assert (
        post(
            customer, f"/v1/escalations/{rid}/replies", {**body, "message": "Changed"}
        ).status_code
        == 409
    )
    assert counts(app)["support_replies"] == 1
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT assigned_agent_id,version FROM support_requests")
            .fetchone()
        )
        assert tuple(row) == ("a1", 5)
    assert customer[0].get("/v1/escalations/" + sid).json["saved"] is True


@pytest.mark.parametrize("state", ["queued", "assigned", "in_review", "resolved"])
def test_reply_id_requires_waiting_state(app, customer, waiting, state, clock):
    rid, _ = waiting
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET state=?,assigned_agent_id=?,resolved_at=? WHERE request_id=?",
                (
                    state,
                    None if state == "queued" else "a1",
                    clock[0] if state == "resolved" else None,
                    rid,
                ),
            )
    assert reply_registration(customer, rid).status_code == 409


def test_stale_reply_and_wrong_operation_do_not_create_content(app, customer, waiting):
    rid, original = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    stale = dict(submission_id=sid, message="Test reply", expected_version=3)
    assert post(customer, f"/v1/escalations/{rid}/replies", stale).status_code == 409
    assert post(customer, "/v1/escalations", payload(sid)).status_code == 404
    assert (
        post(
            customer,
            f"/v1/escalations/{rid}/replies",
            {**stale, "submission_id": original["submission_id"]},
        ).status_code
        == 404
    )
    assert counts(app)["support_replies"] == 0


def test_reply_id_cannot_be_used_for_another_parent(app, customer, waiting):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    _, second = submit(customer)
    body = dict(submission_id=sid, message="Test", expected_version=4)
    assert (
        post(
            customer, f"/v1/escalations/{second.json['request_id']}/replies", body
        ).status_code
        == 404
    )


class FaultyConnection:
    def __init__(self, connection, phase):
        self.connection = connection
        self.phase = phase
        self.failed = False

    def execute(self, sql, *args):
        if self.phase != "commit" and self.phase in sql and not self.failed:
            self.failed = True
            raise sqlite3.OperationalError("private support text must not be logged")
        return self.connection.execute(sql, *args)

    def commit(self):
        if self.phase == "commit" and not self.failed:
            self.failed = True
            self.connection.commit()
            raise TimeoutError("commit acknowledgement lost")
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()


@pytest.mark.parametrize(
    "phase",
    ["INSERT INTO support_requests", "INSERT INTO submission_receipts", "commit"],
)
def test_failed_and_uncertain_saves_recover_with_same_id(
    app, customer, monkeypatch, phase, caplog
):
    sid = register(customer).json["submission_id"]
    original_get = support.get_db
    faults = []

    def faulty_db():
        proxy = FaultyConnection(original_get(), phase)
        faults.append(proxy)
        return proxy

    with monkeypatch.context() as patch:
        patch.setattr(support, "get_db", faulty_db)
        response = post(customer, "/v1/escalations", payload(sid))
    assert response.status_code == 503
    uncertain = phase == "commit"
    assert response.json["error"]["code"] == (
        "SAVE_OUTCOME_UNCERTAIN" if uncertain else "DEPENDENCY_UNAVAILABLE"
    )
    assert "private support text" not in response.text + caplog.text
    status = customer[0].get("/v1/escalations/" + sid).json
    assert status["saved"] is uncertain
    replay = post(customer, "/v1/escalations", payload(sid))
    assert replay.status_code == (200 if uncertain else 201)
    assert counts(app)["support_requests"] == counts(app)["submission_receipts"] == 1


@pytest.mark.parametrize("phase", ["INSERT INTO submission_receipts", "commit"])
def test_reply_commit_failure_does_not_duplicate_or_advance_twice(
    app, customer, waiting, monkeypatch, phase
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    body = dict(submission_id=sid, message="Reviewed reply", expected_version=4)
    original_get = support.get_db
    with monkeypatch.context() as patch:
        patch.setattr(
            support, "get_db", lambda: FaultyConnection(original_get(), phase)
        )
        response = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert response.status_code == 503
    assert response.json["error"]["code"] == (
        "SAVE_OUTCOME_UNCERTAIN" if phase == "commit" else "DEPENDENCY_UNAVAILABLE"
    )
    replay = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert replay.status_code == (200 if phase == "commit" else 201)
    assert counts(app)["support_replies"] == 1
    with app.app_context():
        assert (
            get_db()
            .execute("SELECT version FROM support_requests WHERE request_id=?", (rid,))
            .fetchone()[0]
            == 5
        )


def concurrent_clients(app, customer, total):
    cookie = customer[0].get_cookie("deskguide_session").value
    clients = []
    for _ in range(total):
        client = app.test_client()
        client.set_cookie("deskguide_session", cookie)
        clients.append((client, customer[1]))
    return clients


def test_concurrent_registration_never_exceeds_three(app, customer):
    clients = concurrent_clients(app, customer, 10)
    barrier = Barrier(10)

    def work(api):
        barrier.wait(timeout=10)
        return register(api).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(work, clients))
    assert results.count(201) == 3 and results.count(429) == 7
    assert counts(app)["submission_registrations"] == 3


def test_twenty_concurrent_same_id_submits_create_one_request(app, customer):
    sid = register(customer).json["submission_id"]
    clients = concurrent_clients(app, customer, 20)
    barrier = Barrier(20)

    def work(api):
        barrier.wait(timeout=10)
        response = post(api, "/v1/escalations", payload(sid))
        return response.status_code, response.json.get("request_id")

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(work, clients))
    assert [r[0] for r in results].count(201) == 1
    assert [r[0] for r in results].count(200) == 19
    assert len({r[1] for r in results}) == 1
    assert counts(app)["support_requests"] == counts(app)["submission_receipts"] == 1


def test_concurrent_reply_replays_one_message_and_one_transition(
    app, customer, waiting
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    clients = concurrent_clients(app, customer, 10)
    barrier = Barrier(10)

    def work(api):
        barrier.wait(timeout=10)
        response = post(
            api,
            f"/v1/escalations/{rid}/replies",
            dict(submission_id=sid, message="Reviewed reply", expected_version=4),
        )
        return response.status_code, response.json.get("reply_id")

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(work, clients))
    assert [r[0] for r in results].count(201) == 1
    assert [r[0] for r in results].count(200) == 9
    assert len({r[1] for r in results}) == 1 and counts(app)["support_replies"] == 1


def test_completed_replay_reports_current_state_without_claiming_unread(
    app, customer, waiting, clock
):
    rid, body = waiting
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET state='resolved',resolved_at=? WHERE request_id=?",
                (clock[0], rid),
            )
    replay = post(customer, "/v1/escalations", body)
    assert replay.status_code == 200 and replay.json["state"] == "resolved"
    assert "not been read" not in replay.json["acknowledgement"]


def test_second_application_replays_another_instances_receipt(app, customer, sign_in):
    body, first = submit(customer)
    other = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "TIME_PROVIDER": app.config["TIME_PROVIDER"],
            "SESSION_COOKIE_SECURE": False,
            "SESSION_CLEANUP_N_REQUESTS": None,
        }
    )
    client = other.test_client()
    sign_in(client)
    api = client, {"X-CSRF-Token": client.get("/v1/session").json["csrf_token"]}
    replay = post(api, "/v1/escalations", body)
    assert (
        replay.status_code == 200
        and replay.json["request_id"] == first.json["request_id"]
    )


def test_resolved_retention_blocks_access_before_purge_and_old_id_stays_unknown(
    app, customer, waiting, clock
):
    rid, original = waiting
    reply_sid = reply_registration(customer, rid).json["submission_id"]
    assert (
        post(
            customer,
            f"/v1/escalations/{rid}/replies",
            dict(submission_id=reply_sid, message="Test", expected_version=4),
        ).status_code
        == 201
    )
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET state='resolved',resolved_at=? WHERE request_id=?",
                (clock[0] - support.RETENTION, rid),
            )
    assert (
        customer[0].get("/v1/escalations/" + original["submission_id"]).status_code
        == 404
    )
    assert post(customer, "/v1/escalations", original).status_code == 404
    result = app.test_cli_runner().invoke(args=["cleanup-support"])
    assert result.exit_code == 0, result.output
    assert counts(app) == dict(
        submission_registrations=0,
        support_requests=0,
        submission_receipts=0,
        support_replies=0,
    )
    assert post(customer, "/v1/escalations", original).status_code == 404


def test_reply_racing_resolution_never_revives_terminal_request(
    app, customer, waiting, clock
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    barrier = Barrier(2)
    api = concurrent_clients(app, customer, 1)[0]

    def resolve():
        with app.app_context():
            barrier.wait(timeout=10)
            connection = get_db()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE support_requests SET state='resolved',resolved_at=?,version=version+1 WHERE request_id=?",
                (clock[0], rid),
            )
            connection.commit()

    def reply():
        barrier.wait(timeout=10)
        return post(
            api,
            f"/v1/escalations/{rid}/replies",
            dict(submission_id=sid, message="Race reply", expected_version=4),
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        ending = pool.submit(resolve)
        response = pool.submit(reply)
        ending.result(timeout=15)
        assert response.result(timeout=15) in (201, 409)
    with app.app_context():
        assert (
            get_db()
            .execute("SELECT state FROM support_requests WHERE request_id=?", (rid,))
            .fetchone()[0]
            == "resolved"
        )


def test_reply_ui_reads_current_version_without_request_content(app, customer, waiting):
    rid, original = waiting
    registration = reply_registration(customer, rid)
    assert registration.json["version"] == 4
    sid = registration.json["submission_id"]
    unused = customer[0].get("/v1/escalations/" + sid).json
    assert unused["saved"] is False
    assert unused["state"] == "waiting_for_customer" and unused["version"] == 4
    body = dict(
        submission_id=sid, message="Reviewed reply", expected_version=unused["version"]
    )
    assert post(customer, f"/v1/escalations/{rid}/replies", body).status_code == 201
    for registered_id in (sid, original["submission_id"]):
        status = customer[0].get("/v1/escalations/" + registered_id).json
        assert status["saved"] is True
        assert status["state"] == "in_review" and status["version"] == 5
        assert not {"content", "note", "messages", "assigned_agent_id"} & status.keys()


def test_reply_ui_distinguishes_stale_state_and_payload_conflicts(
    app, customer, waiting
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    body = dict(submission_id=sid, message="Reviewed reply", expected_version=3)
    stale = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert stale.status_code == 409 and stale.json["error"]["code"] == "STALE_VERSION"
    assert stale.json["error"]["retryable"] is False
    assert counts(app)["support_replies"] == 0
    current = customer[0].get("/v1/escalations/" + sid).json
    body["expected_version"] = current["version"]
    assert post(customer, f"/v1/escalations/{rid}/replies", body).status_code == 201
    changed = post(
        customer, f"/v1/escalations/{rid}/replies", {**body, "message": "Different"}
    )
    assert changed.status_code == 409 and changed.json["error"]["code"] == "CONFLICT"
    replay = post(customer, f"/v1/escalations/{rid}/replies", body)
    assert replay.status_code == 200
    assert counts(app)["support_replies"] == 1


@pytest.mark.parametrize("state", ["queued", "assigned", "in_review", "resolved"])
def test_reply_ui_not_waiting_takes_precedence_over_stale_version(
    app, customer, waiting, state, clock
):
    rid, _ = waiting
    sid = reply_registration(customer, rid).json["submission_id"]
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET state=?,version=5,assigned_agent_id=?,resolved_at=? WHERE request_id=?",
                (
                    state,
                    None if state == "queued" else "a1",
                    clock[0] if state == "resolved" else None,
                    rid,
                ),
            )
    registration = reply_registration(customer, rid)
    response = post(
        customer,
        f"/v1/escalations/{rid}/replies",
        dict(submission_id=sid, message="Late reply", expected_version=4),
    )
    for result in (registration, response):
        assert (
            result.status_code == 409
            and result.json["error"]["code"] == "NOT_WAITING_FOR_CUSTOMER"
        )
        assert result.json["error"]["retryable"] is False
    assert counts(app)["support_replies"] == 0
    assert customer[0].get("/v1/escalations/" + sid).json["version"] == 5
