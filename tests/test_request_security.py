"""Concurrent login limits and session-independent readiness regressions."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from conftest import PASSWORD
from sqlalchemy import event

from app import auth
from app.db import get_db


@pytest.mark.parametrize(
    "setting,usernames",
    [
        ("LOGIN_USER_LIMIT", ["customer-one", "customer-one"]),
        ("LOGIN_ADDRESS_LIMIT", ["absent-one", "absent-two"]),
    ],
)
def test_parallel_failures_cannot_exceed_login_limit(
    app, monkeypatch, setting, usernames
):
    app.config[setting] = 1
    clients = [app.test_client(), app.test_client()]
    tokens = [
        client.get("/v1/session/login-token").json["csrf_token"] for client in clients
    ]
    barrier = Barrier(2)
    verify = auth.check_password_hash

    def verify_together(*args):
        barrier.wait(timeout=5)
        return verify(*args)

    monkeypatch.setattr(auth, "check_password_hash", verify_together)

    def attempt(index):
        return (
            clients[index]
            .post(
                "/v1/session/login",
                json={"username": usernames[index], "password": "wrong"},
                headers={"X-CSRF-Token": tokens[index]},
            )
            .status_code
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(attempt, [0, 1]))
    assert sorted(statuses) == [401, 429]
    with app.app_context():
        assert (
            max(r[0] for r in get_db().execute("SELECT failures FROM login_attempts"))
            == 1
        )
        assert (
            get_db().execute("SELECT count(*) FROM active_sessions").fetchone()[0] == 0
        )


def test_limit_reached_during_password_check_cannot_grant_a_session(
    app, client, clock, monkeypatch
):
    app.config["LOGIN_USER_LIMIT"] = 1
    verify = auth.check_password_hash
    token = client.get("/v1/session/login-token").json["csrf_token"]

    def verify_after_another_failure(*args):
        password_ok = verify(*args)
        bucket, _limit = auth.login_buckets("customer-one")[0]
        with sqlite3.connect(app.config["DATABASE"]) as connection:
            connection.execute(
                "INSERT INTO login_attempts VALUES (?, 1, ?)",
                (bucket, clock[0] + 900),
            )
        return password_ok

    monkeypatch.setattr(auth, "check_password_hash", verify_after_another_failure)
    response = client.post(
        "/v1/session/login",
        json={"username": "customer-one", "password": PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 429
    assert client.get("/v1/session").status_code == 401
    with app.app_context():
        assert (
            get_db().execute("SELECT count(*) FROM active_sessions").fetchone()[0] == 0
        )


def test_health_ignores_session_cookies_without_losing_the_login(app, client, sign_in):
    assert sign_in(client).status_code == 200
    reads = []
    with app.app_context():
        engine = app.config["SESSION_SQLALCHEMY"].engine

    def capture(connection, cursor, statement, parameters, context, many):
        if (
            statement.lstrip().upper().startswith("SELECT")
            and "http_sessions" in statement
        ):
            reads.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert "Set-Cookie" not in response.headers
        assert not reads
        assert client.get("/v1/session").status_code == 200
        assert reads
    finally:
        event.remove(engine, "before_cursor_execute", capture)
