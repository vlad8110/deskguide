"""Login, CSRF, expiry, revocation and session-isolation regressions."""

import hashlib
from datetime import datetime

import pytest
from conftest import PASSWORD

from app import create_app
from app.accounts import change_access
from app.db import get_db


def cookie_value(client):
    return client.get_cookie("deskguide_session").value


@pytest.mark.parametrize(
    "name,role",
    [
        ("customer-one", "customer"),
        ("agent-one", "agent"),
        ("admin-one", "administrator"),
    ],
)
def test_login_and_c9_response(client, sign_in, name, role):
    assert sign_in(client, name).status_code == 200
    response = client.get("/v1/session")
    assert response.status_code == 200
    assert response.json["role"] == role
    assert set(response.json) == {
        "role",
        "expires_at",
        "idle_expires_at",
        "csrf_token",
        "correlation_id",
        "contract_version",
    }
    assert response.json["contract_version"] == "0.3.3"


@pytest.mark.parametrize(
    "username,password",
    [("customer-\ud800", PASSWORD), ("customer-one", "invalid-\udfff-password")],
)
def test_login_rejects_unpaired_unicode_surrogates(client, sign_in, username, password):
    response = sign_in(client, username, password)
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_FAILED"
    assert sign_in(client).status_code == 200


def test_session_cookie_is_opaque_and_rotates(client, sign_in, app):
    client.get("/v1/session/login-token")
    before = cookie_value(client)
    login_response = sign_in(client)
    assert login_response.status_code == 200
    after = cookie_value(client)
    assert before != after and "u1" not in after and "customer" not in after
    response = client.get("/v1/session")
    assert "Set-Cookie" not in response.headers
    header = login_response.headers["Set-Cookie"]
    assert "HttpOnly" in header and "SameSite=Lax" in header
    with app.app_context():
        row = get_db().execute("SELECT session_hash FROM active_sessions").fetchone()
        assert row[0] == hashlib.sha256(after.encode()).hexdigest()
        assert get_db().execute("SELECT COUNT(*) FROM http_sessions").fetchone()[0] == 1


def test_secure_cookie_profile(app, tmp_path, sign_in):
    secure = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "SESSION_COOKIE_SECURE": True,
        }
    )
    client = secure.test_client()
    response = client.get("/v1/session/login-token", base_url="https://localhost")
    assert "; Secure;" in response.headers["Set-Cookie"]


def test_missing_and_unknown_session_return_401(client):
    assert client.get("/v1/session").status_code == 401
    client.set_cookie("deskguide_session", "unknown-session-token")
    assert client.get("/v1/session").status_code == 401


@pytest.mark.parametrize("password", ["incorrect", "' OR 1=1 --"])
def test_wrong_password_is_generic(client, sign_in, password):
    response = sign_in(client, password=password)
    assert response.status_code == 401
    assert response.json["error"]["message"] == "Username or password is incorrect."
    assert client.get("/v1/session").status_code == 401


def test_unknown_user_gets_same_error(client, sign_in):
    response = sign_in(client, "missing-user")
    assert response.status_code == 401
    assert response.json["error"]["message"] == "Username or password is incorrect."


def test_cannot_choose_identity_or_role_at_login(client, sign_in):
    response = sign_in(client, role="administrator", customer_id="c2")
    assert response.status_code == 400
    assert client.get("/v1/session").status_code == 401


def test_login_requires_csrf(client):
    response = client.post(
        "/v1/session/login", json={"username": "customer-one", "password": PASSWORD}
    )
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CSRF_FAILED"


def test_prelogin_csrf_expires(client, clock):
    token = client.get("/v1/session/login-token").json["csrf_token"]
    clock[0] += 600
    assert (
        client.post(
            "/v1/session/login",
            json={"username": "customer-one", "password": PASSWORD},
            headers={"X-CSRF-Token": token},
        ).status_code
        == 403
    )


@pytest.mark.parametrize("token", [None, "invalid"])
def test_protected_write_requires_session_csrf(client, sign_in, token):
    sign_in(client)
    headers = {} if token is None else {"X-CSRF-Token": token}
    response = client.post("/test/write", json={}, headers=headers)
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CSRF_FAILED"


def test_valid_write_and_current_session_logout(client, sign_in, app):
    sign_in(client)
    second = app.test_client()
    sign_in(second)
    token = client.get("/v1/session").json["csrf_token"]
    assert (
        client.post("/test/write", json={}, headers={"X-CSRF-Token": token}).status_code
        == 200
    )
    stale_cookie = cookie_value(client)
    assert (
        client.post("/v1/session/logout", headers={"X-CSRF-Token": token}).status_code
        == 204
    )
    assert client.get("/v1/session").status_code == 401
    client.set_cookie("deskguide_session", stale_cookie)
    assert client.get("/v1/session").status_code == 401
    assert (
        client.post("/v1/session/logout", headers={"X-CSRF-Token": token}).status_code
        == 401
    )
    assert second.get("/v1/session").status_code == 200


def test_stale_library_session_write_cannot_undo_logout(client, sign_in, app):
    sign_in(client)
    sid = cookie_value(client)
    with app.app_context():
        data = get_db().execute("SELECT data FROM http_sessions").fetchone()[0]
    token = client.get("/v1/session").json["csrf_token"]
    client.post("/v1/session/logout", headers={"X-CSRF-Token": token})
    with app.app_context():
        with get_db() as db:
            db.execute(
                "INSERT INTO http_sessions (session_id, data, expiry) VALUES (?, ?, ?)",
                ("deskguide:" + sid, data, "2099-01-01 00:00:00"),
            )
    client.set_cookie("deskguide_session", sid)
    assert client.get("/v1/session").status_code == 401


def test_session_cannot_be_reused_after_second_login(client, sign_in, app):
    sign_in(client)
    old_cookie = cookie_value(client)
    sign_in(client, "admin-one")
    assert cookie_value(client) != old_cookie
    replay = app.test_client()
    replay.set_cookie("deskguide_session", old_cookie)
    assert replay.get("/v1/session").status_code == 401


def test_idle_expiry(client, sign_in, clock):
    sign_in(client)
    clock[0] += 1800
    assert client.get("/v1/session").status_code == 401


def test_idle_renewal_never_moves_absolute_expiry(client, sign_in, clock):
    sign_in(client)
    initial = client.get("/v1/session").json
    for _ in range(20):
        clock[0] += 1000
        result = client.get("/v1/session")
        assert result.status_code == 200
        assert result.json["expires_at"] == initial["expires_at"]
    assert result.json["idle_expires_at"] > initial["idle_expires_at"]
    clock[0] = int(datetime.fromisoformat(initial["expires_at"]).timestamp())
    assert client.get("/v1/session").status_code == 401


def test_session_persists_between_app_instances(app, client, sign_in):
    sign_in(client)
    other = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
            "TIME_PROVIDER": app.config["TIME_PROVIDER"],
            "SESSION_COOKIE_SECURE": False,
        }
    )
    second = other.test_client()
    second.set_cookie("deskguide_session", cookie_value(client))
    assert second.get("/v1/session").json["role"] == "customer"


def test_role_and_permission_changes_revoke_all_sessions(app, client, sign_in):
    sign_in(client, "agent-one")
    second = app.test_client()
    sign_in(second, "agent-one")
    with app.app_context():
        change_access("a1", "agent", None, ["reviewer"])
    assert client.get("/v1/session").status_code == 401
    assert second.get("/v1/session").status_code == 401


def test_disabled_account_is_denied(app, client, sign_in):
    sign_in(client)
    with app.app_context():
        with get_db() as db:
            db.execute("UPDATE users SET active = 0 WHERE user_id = 'u1'")
    assert client.get("/v1/session").status_code == 401
    assert sign_in(client).status_code == 401


def test_user_login_throttle_and_reset(client, sign_in, clock):
    for _ in range(5):
        assert sign_in(client, password="wrong").status_code == 401
    blocked = sign_in(client)
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    clock[0] += 901
    assert sign_in(client).status_code == 200


def test_address_login_throttle_blocks_username_rotation(app, client, sign_in):
    app.config["LOGIN_ADDRESS_LIMIT"] = 2
    assert sign_in(client, "absent-one").status_code == 401
    assert sign_in(client, "absent-two").status_code == 401
    assert sign_in(client, "customer-one").status_code == 429


def test_password_reset_revokes_existing_login(app, client, sign_in):
    sign_in(client)
    result = app.test_cli_runner().invoke(
        args=["set-password", "customer-one"], input=PASSWORD + "\n" + PASSWORD + "\n"
    )
    assert result.exit_code == 0
    assert PASSWORD not in result.output
    assert client.get("/v1/session").status_code == 401
