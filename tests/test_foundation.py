"""Startup, schema, provisioning and safe-error regressions."""

import sqlite3
import warnings
from html.parser import HTMLParser
from urllib.parse import urlsplit
from uuid import UUID

import pytest
from flask import template_rendered
from sqlalchemy.exc import SQLAlchemyError

from app import JsonSessionSerializer, create_app
from app.db import get_db, init_db


def test_health_and_safe_server_owned_correlation(client):
    response = client.get(
        "/health", headers={"X-Correlation-ID": "untrusted-client-value"}
    )
    assert response.status_code == 200 and response.json["status"] == "ok"
    UUID(response.headers["X-Correlation-ID"])
    assert response.json["correlation_id"] != "untrusted-client-value"
    assert response.headers["Cache-Control"] == "no-store"


def test_uninitialized_database_has_clear_readiness_status(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "new.sqlite3")})
    assert app.test_client().get("/health").status_code == 503
    assert app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
    assert app.test_client().get("/health").status_code == 200


def test_init_db_preserves_records(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0 and "already initialized" in result.output
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 5
        assert get_db().execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert get_db().execute("PRAGMA foreign_key_check").fetchall() == []


def test_unknown_schema_version_does_not_reinitialize(app):
    with app.app_context():
        get_db().execute("PRAGMA user_version = 99")
        with pytest.raises(RuntimeError):
            init_db()
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 5


def test_cross_customer_feedback_is_rejected_by_database(app, clock):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO inquiries (inquiry_id,customer_id,route,created_at,expires_at) "
            "VALUES ('i1','c1','ai',?,?)",
            (clock[0], clock[0] + 100),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO feedback VALUES ('f1','i1','c2','helpful',NULL,?)",
                (clock[0],),
            )
        db.rollback()


def test_registered_submission_cannot_be_assigned_to_other_customer(
    app, support_records, clock
):
    with app.app_context():
        get_db().execute(
            "INSERT INTO submission_registrations "
            "(submission_id,customer_id,operation,registered_at,expires_at) "
            "VALUES ('s3','c1','escalation',?,?)",
            (clock[0], clock[0] + 1800),
        )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            get_db().execute(
                "INSERT INTO support_requests (request_id,submission_id,customer_id,content,"
                "reason,created_at) VALUES ('r3','s3','c2','test','customer_requested',?)",
                (clock[0],),
            )


def test_same_submission_cannot_create_second_request(app, support_records, clock):
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute(
                "INSERT INTO support_requests (request_id,submission_id,customer_id,content,"
                "reason,created_at) VALUES ('r3','s1','c1','test','customer_requested',?)",
                (clock[0],),
            )


def test_customer_requires_existing_mapping(app):
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute(
                "INSERT INTO users VALUES ('bad','bad-user','hash','customer',NULL,1,1,0)"
            )


def test_no_ordinary_question_or_answer_column(app):
    with app.app_context():
        names = {row[1] for row in get_db().execute("PRAGMA table_info(inquiries)")}
        assert not {"question", "answer", "content"} & names


def test_home_and_browser_assets(client, sign_in):
    response = client.get("/")
    assert response.status_code == 200 and b"Sign in to DeskGuide" in response.data
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/static/workspace.js").status_code == 200
    assert client.get("/static/workspace.css").status_code == 200
    sign_in(client)
    assert b"Welcome, customer-one" in client.get("/").data


def test_native_login_form_never_sends_credentials_in_the_url(client, caplog):
    class SignInForm(HTMLParser):
        attributes = None

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "form" and values.get("id") == "sign-in":
                self.attributes = values

    form = SignInForm()
    form.feed(client.get("/").text)
    assert form.attributes is not None
    assert form.attributes.get("method", "get").lower() == "post"
    action = form.attributes.get("action", "/")
    assert action == "/v1/session/login"
    credentials = {
        "username": "fictional-native-user",
        "password": "Native-only-test-secret-42!",
    }
    response = client.open(
        action, method=form.attributes["method"].upper(), data=credentials
    )
    assert urlsplit(response.request.url).query == ""
    assert response.request.form["password"] == credentials["password"]
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CSRF_FAILED"
    assert credentials["password"] not in response.text + caplog.text
    assert client.get("/v1/session").status_code == 401


@pytest.mark.parametrize(
    ("username", "role"),
    [
        ("customer-one", "customer"),
        ("agent-one", "agent"),
        ("admin-one", "administrator"),
    ],
)
def test_home_template_receives_only_display_account_fields(
    app, client, sign_in, username, role
):
    contexts = []

    def capture_template(sender, template, context, **extra):
        contexts.append(context)

    sign_in(client, username)
    with template_rendered.connected_to(capture_template, app):
        response = client.get("/")

    assert response.status_code == 200
    assert dict(contexts[0]["account"]) == {"username": username, "role": role}
    assert f"Welcome, {username}" in response.text


def test_signed_out_home_template_has_no_account(app, client):
    contexts = []

    def capture_template(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture_template, app):
        response = client.get("/")

    assert response.status_code == 200
    assert contexts[0]["account"] is None
    assert "Sign in to DeskGuide" in response.text


def test_public_account_creation_is_unavailable(client):
    assert client.get("/v1/users").status_code == 404
    assert client.post("/v1/users", json={"role": "administrator"}).status_code in {
        401,
        404,
    }


def test_oversized_request_returns_safe_error(client):
    response = client.post(
        "/v1/session/login", data=b"x" * 20000, content_type="application/json"
    )
    assert response.status_code in {403, 413}
    assert "error" in response.json


def test_failures_do_not_expose_internal_errors(app, client, caplog):
    @app.get("/test/failure")
    def fail():
        raise RuntimeError("private-secret-and-internal-path")

    response = client.get("/test/failure")
    assert response.status_code == 500
    assert "private-secret" not in response.text
    record = next(r for r in caplog.records if "internal_error" in r.message)
    assert record.exc_info is not None and record.exc_info[0] is RuntimeError
    assert response.headers["X-Correlation-ID"] in record.message
    assert "Traceback" in caplog.text


@pytest.mark.parametrize("error_type", [sqlite3.OperationalError, SQLAlchemyError])
def test_storage_failures_log_traceback_without_exposing_details(
    app, client, caplog, error_type
):
    @app.get("/test/storage-failure")
    def fail():
        raise error_type("synthetic internal storage failure")

    response = client.get("/test/storage-failure")
    assert response.status_code == 503
    assert response.json["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "synthetic internal storage failure" not in response.text
    record = next(r for r in caplog.records if "storage_unavailable" in r.message)
    assert record.exc_info is not None and record.exc_info[0] is error_type
    assert response.headers["X-Correlation-ID"] in record.message
    assert "Traceback" in caplog.text


def test_warning_filter_does_not_hide_other_deprecations():
    known = (
        "datetime.datetime.utcnow() is deprecated and scheduled for removal "
        "in a future version. Use timezone-aware objects."
    )
    backend = "flask_session.sqlalchemy.sqlalchemy"
    with warnings.catch_warnings(record=True) as recorded:
        warnings.warn_explicit(known, DeprecationWarning, __file__, 1, module=backend)
        warnings.warn_explicit(known, DeprecationWarning, __file__, 2, module=__name__)
        warnings.warn_explicit(
            "A different deprecation.", DeprecationWarning, __file__, 3, module=backend
        )
    assert [str(w.message) for w in recorded] == [known, "A different deprecation."]


def test_session_serializer_refuses_non_json():
    with pytest.raises((ValueError, UnicodeDecodeError)):
        JsonSessionSerializer().decode(b"\x80\x04malicious-pickle")


def test_provisioning_uses_hidden_prompt_and_hashes(app):
    result = app.test_cli_runner().invoke(
        args=["create-user", "new-agent", "--role", "agent"],
        input="A-new-local-password-42!\nA-new-local-password-42!\n",
    )
    assert result.exit_code == 0
    assert "A-new-local-password" not in result.output
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT password_hash FROM users WHERE username='new-agent'")
            .fetchone()
        )
        assert row[0].startswith("scrypt:") and row[0] != "A-new-local-password-42!"


def test_provisioning_does_not_allow_unknown_customer(app):
    result = app.test_cli_runner().invoke(
        args=[
            "create-user",
            "new-user",
            "--role",
            "customer",
            "--customer-id",
            "missing",
        ],
        input="A-new-local-password-42!\nA-new-local-password-42!\n",
    )
    assert result.exit_code != 0


def test_demo_seed_does_not_overwrite_existing_accounts(app):
    result = app.test_cli_runner().invoke(
        args=["seed-demo"], input="A-new-local-password-42!\nA-new-local-password-42!\n"
    )
    assert result.exit_code != 0 and "already exist" in result.output


def test_demo_seed_is_usable_from_a_new_database(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "demo.sqlite3"),
            "SESSION_COOKIE_SECURE": False,
        }
    )
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    result = runner.invoke(
        args=["seed-demo"], input="A-new-local-password-42!\nA-new-local-password-42!\n"
    )
    assert result.exit_code == 0 and "A-new-local-password" not in result.output
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4
        assert (
            get_db().execute("SELECT COUNT(*) FROM user_permissions").fetchone()[0] == 0
        )


def test_cleanup_preserves_unexpired_revocation_tombstones(app, client, sign_in, clock):
    sign_in(client)
    token = client.get("/v1/session").json["csrf_token"]
    client.post("/v1/session/logout", headers={"X-CSRF-Token": token})
    runner = app.test_cli_runner()
    assert runner.invoke(args=["cleanup-auth"]).exit_code == 0
    with app.app_context():
        assert (
            get_db().execute("SELECT revoked FROM active_sessions").fetchone()[0] == 1
        )
    clock[0] += 28801
    assert runner.invoke(args=["cleanup-auth"]).exit_code == 0
    with app.app_context():
        assert (
            get_db().execute("SELECT COUNT(*) FROM active_sessions").fetchone()[0] == 0
        )


def test_invalid_access_change_rolls_back_existing_role(app, client, sign_in):
    sign_in(client, "agent-one")
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "set-access",
            "agent-one",
            "--role",
            "customer",
            "--customer-id",
            "does-not-exist",
        ]
    )
    assert result.exit_code != 0
    assert client.get("/v1/session").json["role"] == "agent"
