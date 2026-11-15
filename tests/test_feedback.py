"""C6a through the signed-in customer API and SQLite persistence."""

import sqlite3
from uuid import uuid4

import pytest

from app import feedback
from app.db import get_db


def submit(client, **payload):
    token = client.get("/v1/session").json["csrf_token"]
    return client.post("/v1/feedback", json=payload, headers={"X-CSRF-Token": token})


def add_inquiry(app, clock, *, outcome="answered", expires_in=86400):
    inquiry_id = str(uuid4())
    with app.app_context(), get_db() as db:
        db.execute(
            "INSERT INTO inquiries "
            "(inquiry_id, customer_id, route, outcome, answer_id, configuration_version, created_at, expires_at) "
            "VALUES (?, 'c1', 'ai', ?, ?, 'fictional-config', ?, ?)",
            (
                inquiry_id,
                outcome,
                str(uuid4()) if outcome == "answered" else None,
                clock[0] - 1,
                clock[0] + expires_in,
            ),
        )
    return inquiry_id


def test_answered_feedback_uses_owned_inquiry_and_rejects_replacement(
    app, client, sign_in, clock
):
    inquiry_id = add_inquiry(app, clock)
    sign_in(client)
    first = submit(
        client,
        inquiry_id=inquiry_id,
        rating="not_helpful",
        category="wrong_source",
        comment="  Cafe\u0301  ",
    )
    assert first.status_code == 201
    assert first.json["state"] == "pending_review"
    assert first.json["correlation_id"] == first.headers["X-Correlation-ID"]

    retry = submit(client, inquiry_id=inquiry_id, rating="helpful")
    assert (retry.status_code, retry.json["error"]["code"]) == (409, "CONFLICT")
    with app.app_context():
        rows = (
            get_db()
            .execute(
                "SELECT feedback_id, rating, category, comment, outcome, route, "
                "configuration_version, answer_id FROM feedback JOIN inquiries "
                "USING (inquiry_id, customer_id)"
            )
            .fetchall()
        )
    assert len(rows) == 1
    assert tuple(rows[0])[:-1] == (
        first.json["feedback_id"],
        "not_helpful",
        "wrong_source",
        "Café",
        "answered",
        "ai",
        "fictional-config",
    )
    assert rows[0]["answer_id"] is not None


def test_feedback_on_actual_unanswered_inquiry(app, client, sign_in):
    sign_in(client)
    token = client.get("/v1/session").json["csrf_token"]
    inquiry = client.post(
        "/v1/inquiries",
        json={"requested_operation": "ask_question", "question": "Demo question"},
        headers={"X-CSRF-Token": token},
    )
    assert inquiry.status_code == 200 and inquiry.json["answer_id"] is None
    inquiry_id = inquiry.json["inquiry_id"]
    for category in ("wrong_source", ["unclear"]):
        rejected = submit(
            client, inquiry_id=inquiry_id, rating="not_helpful", category=category
        )
        assert rejected.status_code == 400
    saved = submit(
        client,
        inquiry_id=inquiry_id,
        rating="not_helpful",
        category="fallback_unhelpful",
    )
    assert saved.status_code == 201
    with app.app_context():
        row = (
            get_db()
            .execute(
                "SELECT category, answer_id FROM feedback JOIN inquiries USING (inquiry_id)"
            )
            .fetchone()
        )
    assert tuple(row) == ("fallback_unhelpful", None)


@pytest.mark.parametrize(
    "extra",
    [
        {"rating": "good"},
        {"category": "unclear"},
        {"answer_id": "supplied-by-caller"},
        {"comment": "😀" * 501},
        {"comment": "control\x00character"},
        {"comment": 23},
    ],
)
def test_invalid_payload_does_not_save(app, client, sign_in, clock, extra):
    inquiry_id = add_inquiry(app, clock)
    sign_in(client)
    response = submit(
        client, **({"inquiry_id": inquiry_id, "rating": "helpful"} | extra)
    )
    assert (response.status_code, response.json["error"]["code"]) == (
        400,
        "VALIDATION_FAILED",
    )
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0


def test_access_and_expiry(app, client, sign_in, clock):
    owned = add_inquiry(app, clock)
    expired = add_inquiry(app, clock, expires_in=0)
    processing = add_inquiry(app, clock, outcome="processing")
    payload = {"inquiry_id": owned, "rating": "helpful"}
    assert client.post("/v1/feedback", json=payload).status_code == 401
    sign_in(client)
    assert client.post("/v1/feedback", json=payload).status_code == 403
    for inquiry_id in (expired, processing, str(uuid4())):
        response = submit(client, inquiry_id=inquiry_id, rating="helpful")
        assert (response.status_code, response.json["error"]["code"]) == (
            404,
            "NOT_FOUND",
        )
    for username, status in [
        ("customer-two", 404),
        ("agent-one", 403),
        ("admin-one", 403),
    ]:
        other = app.test_client()
        sign_in(other, username)
        assert submit(other, **payload).status_code == status
    assert submit(client, **payload, comment="😀" * 500).status_code == 201


def test_cleanup_purges_only_expired_inquiries_and_feedback(
    app, client, sign_in, clock
):
    short = add_inquiry(app, clock, expires_in=1)
    long = add_inquiry(app, clock)
    sign_in(client)
    for inquiry_id in (short, long):
        assert (
            submit(client, inquiry_id=inquiry_id, rating="helpful").status_code == 201
        )
    clock[0] += 1
    result = app.test_cli_runner().invoke(args=["cleanup-inquiries"])
    assert result.exit_code == 0
    with app.app_context():
        db = get_db()
        assert [row[0] for row in db.execute("SELECT inquiry_id FROM inquiries")] == [
            long
        ]
        assert [row[0] for row in db.execute("SELECT inquiry_id FROM feedback")] == [
            long
        ]


def test_scheduled_cleanup_catches_up_and_purges_at_the_next_daily_run(
    app, clock, monkeypatch
):
    expired = add_inquiry(app, clock, expires_in=0)
    next_day = add_inquiry(app, clock, expires_in=100)
    retained = add_inquiry(app, clock, expires_in=2 * 86400)
    purge = feedback.purge_expired_inquiries
    waits = []
    remaining = []

    def fail_once():
        if not waits:
            raise sqlite3.OperationalError("temporary lock")
        return purge()

    class Schedule:
        def is_set(self):
            return len(waits) == 3

        def wait(self, seconds):
            waits.append(seconds)
            with app.app_context():
                remaining.append(
                    {
                        row[0]
                        for row in get_db().execute("SELECT inquiry_id FROM inquiries")
                    }
                )
            if seconds == 86400:
                clock[0] += seconds

    monkeypatch.setattr(feedback, "purge_expired_inquiries", fail_once)
    feedback.run_inquiry_cleanup(app, Schedule(), app.logger)
    assert waits == [300, 86400, 86400]
    assert remaining == [
        {expired, next_day, retained},
        {next_day, retained},
        {retained},
    ]
