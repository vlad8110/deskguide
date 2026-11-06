"""Session cleanup, request writes, proxy trust and HTTP error regressions."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from conftest import PASSWORD, PASSWORD_HASH
from dotenv import dotenv_values
from flask import jsonify, request
from flask_session.base import ServerSideSessionInterface
from sqlalchemy import event
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import TooManyRequests, Unauthorized, abort

from app import auth, create_app
from app.db import get_db


@pytest.fixture
def auth_writes(app):
    """Observe real writes from both SQLite access paths without logging values."""
    writes = []

    def capture(statement):
        command = statement.lstrip().upper()
        if command.startswith(("UPDATE ", "INSERT ", "DELETE ")):
            writes.append(command.split()[0])

    def trace_application_sql():
        get_db().set_trace_callback(capture)

    def trace_session_sql(connection, cursor, statement, parameters, context, many):
        capture(statement)

    app.before_request_funcs[None].insert(0, trace_application_sql)
    with app.app_context():
        engine = app.config["SESSION_SQLALCHEMY"].engine
    event.listen(engine, "before_cursor_execute", trace_session_sql)
    yield writes
    event.remove(engine, "before_cursor_execute", trace_session_sql)


def test_cleanup_auth_removes_abandoned_expired_http_sessions(app):
    for _ in range(3):
        assert app.test_client().get("/v1/session/login-token").status_code == 200
    with app.app_context():
        with get_db() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM http_sessions ORDER BY id")]
            db.executemany(
                "UPDATE http_sessions SET expiry = ? WHERE id = ?",
                [("2000-01-01 00:00:00", ids[0]), (None, ids[1])],
            )
    result = app.test_cli_runner().invoke(args=["cleanup-auth"])
    assert result.exit_code == 0
    with app.app_context():
        assert [r[0] for r in get_db().execute("SELECT id FROM http_sessions")] == [
            ids[2]
        ]


def test_request_cleanup_removes_expired_sessions_without_a_scheduler(app, monkeypatch):
    other = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "SESSION_COOKIE_SECURE": False,
            "DUMMY_PASSWORD_HASH": PASSWORD_HASH,
        }
    )
    assert isinstance(other.session_interface, ServerSideSessionInterface)
    assert other.session_interface.cleanup_n_requests == 100
    with app.app_context():
        with get_db() as db:
            db.execute(
                "INSERT INTO http_sessions (session_id, data, expiry) VALUES (?, ?, ?)",
                ("deskguide:abandoned", b"{}", "2000-01-01 00:00:00"),
            )
    monkeypatch.setattr("flask_session.base.random.randint", lambda *_: 0)
    assert other.test_client().get("/health").status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM http_sessions").fetchone()[0] == 0


def test_activity_writes_are_coalesced_and_cookie_refreshes_only_on_heartbeat(
    app, client, sign_in, clock, auth_writes
):
    assert sign_in(client).status_code == 200
    started = clock[0]
    for delta in [1, 15, 59]:
        clock[0] = started + delta
        auth_writes.clear()
        response = client.get("/v1/session")
        assert response.status_code == 200
        assert not auth_writes
        assert "Set-Cookie" not in response.headers
    clock[0] = started + 60
    auth_writes.clear()
    response = client.get("/v1/session")
    assert response.status_code == 200
    assert auth_writes == ["UPDATE", "UPDATE"]
    assert "Set-Cookie" in response.headers
    with app.app_context():
        assert (
            get_db().execute("SELECT last_seen FROM active_sessions").fetchone()[0]
            == clock[0]
        )
    auth_writes.clear()
    assert client.get("/v1/session").status_code == 200
    assert not auth_writes


@pytest.mark.parametrize(
    "path", ["/health", "/static/workspace.css", "/static/workspace.js"]
)
@pytest.mark.parametrize("signed_in", [False, True])
def test_health_and_assets_do_not_refresh_existing_sessions(
    client, sign_in, clock, auth_writes, path, signed_in
):
    if signed_in:
        assert sign_in(client).status_code == 200
    else:
        client.get("/v1/session/login-token")
    clock[0] += 60
    auth_writes.clear()
    response = client.get(path)
    assert response.status_code == 200
    assert not auth_writes
    assert "Set-Cookie" not in response.headers


def test_reported_idle_deadline_matches_saved_activity(client, sign_in, clock):
    assert sign_in(client).status_code == 200
    initial = client.get("/v1/session").json["idle_expires_at"]
    clock[0] += 59
    assert client.get("/v1/session").json["idle_expires_at"] == initial
    clock[0] = int(datetime.fromisoformat(initial).timestamp())
    assert client.get("/v1/session").status_code == 401


def test_health_polling_does_not_keep_a_login_alive(client, sign_in, clock):
    assert sign_in(client).status_code == 200
    for _ in range(30):
        clock[0] += 60
        assert client.get("/health").status_code == 200
    assert client.get("/v1/session").status_code == 401


@pytest.mark.parametrize("revoked,expected", [(False, 200), (True, 401)])
def test_overlapping_refresh_or_revocation_is_rechecked(
    app, client, sign_in, clock, monkeypatch, revoked, expected
):
    assert sign_in(client).status_code == 200
    clock[0] += 60
    read_record = auth._session_record
    raced = False

    def read_then_allow_other_worker(user_id):
        nonlocal raced
        record = read_record(user_id)
        if not raced:
            raced = True
            # Another worker commits after this request's read, before its update.
            with sqlite3.connect(app.config["DATABASE"]) as connection:
                connection.execute(
                    "UPDATE active_sessions SET revoked = ?, last_seen = ?",
                    (int(revoked), record["last_seen"] if revoked else clock[0]),
                )
        return record

    monkeypatch.setattr(auth, "_session_record", read_then_allow_other_worker)
    assert client.get("/v1/session").status_code == expected
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT revoked, last_seen FROM active_sessions")
            .fetchone()
        )
        assert row["revoked"] == int(revoked)
        assert row["last_seen"] == clock[0] - (60 if revoked else 0)


def test_heartbeat_refreshes_storage_expiry_and_expired_storage_is_denied(
    app, client, sign_in, clock, monkeypatch
):
    class SessionClock(datetime):
        @classmethod
        def utcnow(cls):
            return cls.fromtimestamp(clock[0], timezone.utc).replace(tzinfo=None)

    monkeypatch.setattr("flask_session.sqlalchemy.sqlalchemy.datetime", SessionClock)
    assert sign_in(client).status_code == 200
    started = clock[0]

    def stored_expiry():
        with app.app_context():
            text = get_db().execute("SELECT expiry FROM http_sessions").fetchone()[0]
        return int(
            datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()
        )

    assert stored_expiry() == started + 1800
    clock[0] += 59
    assert client.get("/v1/session").status_code == 200
    assert stored_expiry() == started + 1800
    clock[0] += 1
    assert client.get("/v1/session").status_code == 200
    assert stored_expiry() == started + 60 + 1800
    clock[0] += 1800
    assert client.get("/v1/session").status_code == 401


def proxy_app(app, **config):
    other = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "TIME_PROVIDER": app.config["TIME_PROVIDER"],
            "SESSION_COOKIE_SECURE": False,
            "SESSION_CLEANUP_N_REQUESTS": None,
            "DUMMY_PASSWORD_HASH": PASSWORD_HASH,
            "LOGIN_ADDRESS_LIMIT": 2,
            **config,
        }
    )

    @other.get("/test/origin")
    def origin():
        return jsonify(
            address=request.remote_addr, scheme=request.scheme, host=request.host
        )

    return other


@pytest.mark.parametrize("trusted", [False, True])
def test_proxy_clients_have_separate_buckets_only_with_explicit_trust(app, trusted):
    other = proxy_app(app, PROXY_X_FOR=int(trusted), PROXY_X_PROTO=int(trusted))
    first, second = other.test_client(), other.test_client()

    def login(client, ip, username, password):
        token = client.get("/v1/session/login-token").json["csrf_token"]
        return client.post(
            "/v1/session/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": token, "X-Forwarded-For": ip},
            environ_base={"REMOTE_ADDR": "10.0.0.1"},
        )

    assert login(first, "198.51.100.1", "absent-one", "wrong").status_code == 401
    assert login(first, "198.51.100.1", "absent-two", "wrong").status_code == 401
    assert login(first, "198.51.100.1", "customer-one", PASSWORD).status_code == 429
    response = login(second, "198.51.100.2", "customer-one", PASSWORD)
    assert response.status_code == (200 if trusted else 429)


@pytest.mark.parametrize(
    "hops,expected", [(0, "10.0.0.1"), (1, "10.0.0.2"), (2, "198.51.100.2")]
)
def test_proxy_hop_count_and_header_boundaries(app, hops, expected):
    other = proxy_app(app, PROXY_X_FOR=hops, PROXY_X_PROTO=1 if hops else 0)
    response = other.test_client().get(
        "/test/origin",
        headers={
            "X-Forwarded-For": "192.0.2.99, 198.51.100.2, 10.0.0.2",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "untrusted.example",
        },
        environ_base={"REMOTE_ADDR": "10.0.0.1"},
    )
    assert response.json == {
        "address": expected,
        "scheme": "https" if hops else "http",
        "host": "localhost",
    }


@pytest.mark.parametrize(
    "setting,value", [("PROXY_X_FOR", -1), ("PROXY_X_PROTO", "invalid")]
)
def test_invalid_proxy_trust_fails_at_startup(tmp_path, setting, value):
    with pytest.raises(RuntimeError, match="PROXY_X_"):
        create_app(
            {"TESTING": True, "DATABASE": str(tmp_path / "bad.sqlite3"), setting: value}
        )


@pytest.mark.parametrize("secret", [None, ""])
def test_missing_secret_refuses_nonlocal_startup(tmp_path, monkeypatch, secret):
    monkeypatch.delenv("DESKGUIDE_LOCAL_HTTP", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    database = tmp_path / "server.sqlite3"
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"DATABASE": str(database), "SECRET_KEY": secret})
    assert not database.exists()


def test_explicit_secure_profile_and_local_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("DESKGUIDE_LOCAL_HTTP", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test-configuration-key-for-this-test-only")
    secure = create_app({"DATABASE": str(tmp_path / "secure.sqlite3")})
    assert secure.config["SESSION_COOKIE_SECURE"] is True
    monkeypatch.delenv("SECRET_KEY")
    monkeypatch.setenv("DESKGUIDE_LOCAL_HTTP", "1")
    local = create_app({"DATABASE": str(tmp_path / "local.sqlite3")})
    assert local.secret_key and local.config["SESSION_COOKIE_SECURE"] is False
    assert local.test_client().get("/v1/session/login-token").status_code == 200
    assert (
        local.test_client().get("/", base_url="http://untrusted.example").status_code
        == 400
    )


def test_environment_template_does_not_enable_insecure_cookies():
    settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env.example")
    assert settings.get("DESKGUIDE_LOCAL_HTTP") != "1"


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "UNAUTHENTICATED"),
        (403, "FORBIDDEN"),
        (415, "UNSUPPORTED_MEDIA_TYPE"),
        (429, "RATE_LIMITED"),
    ],
)
def test_werkzeug_errors_keep_status_and_safe_contract_code(app, client, status, code):
    @app.get("/test/http-error")
    def failure():
        abort(status, description="private-exception-detail")

    response = client.get("/test/http-error")
    assert response.status_code == status
    assert response.json["error"]["code"] == code
    assert (
        response.json["error"]["correlation_id"] == response.headers["X-Correlation-ID"]
    )
    assert "private-exception-detail" not in response.text


@pytest.mark.parametrize(
    "method,path,status,code",
    [
        ("post", "/missing", 404, "NOT_FOUND"),
        ("delete", "/missing", 404, "NOT_FOUND"),
        ("post", "/health", 405, "METHOD_NOT_ALLOWED"),
    ],
)
def test_routing_errors_are_not_replaced_by_auth_or_csrf(
    client, method, path, status, code
):
    response = getattr(client, method)(path)
    assert response.status_code == status
    assert response.json["error"]["code"] == code
    if status == 405:
        assert "GET" in response.headers["Allow"]


def test_http_error_headers_survive_json_conversion(app, client):
    @app.get("/test/rate-limit")
    def limited():
        raise TooManyRequests(retry_after=17)

    @app.get("/test/challenge")
    def challenge():
        raise Unauthorized(www_authenticate=WWWAuthenticate("Bearer"))

    response = client.get("/test/rate-limit")
    assert response.headers["Retry-After"] == "17"
    assert response.json["error"]["retryable"] is True
    assert client.get("/test/challenge").headers["WWW-Authenticate"] == "Bearer"
