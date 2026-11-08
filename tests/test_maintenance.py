"""Minimal session payloads and consistent stable-ID account updates."""

import json
import sqlite3

import pytest
from conftest import PASSWORD
from werkzeug.security import check_password_hash

from app import accounts
from app.clock import now, timestamp
from app.db import get_db


def test_shared_clock_controls_account_creation(app, clock):
    clock[0] += 123
    with app.app_context():
        user_id = accounts.create_user("new-account", PASSWORD, "customer", "c1")
        created = (
            get_db()
            .execute("SELECT created_at FROM users WHERE user_id=?", (user_id,))
            .fetchone()[0]
        )
        assert created == now() == clock[0]
        assert timestamp(created).endswith("Z")


def test_session_storage_does_not_duplicate_registry_times(app, client, sign_in, clock):
    assert sign_in(client).status_code == 200
    for advance in [0, 60]:
        clock[0] += advance
        assert client.get("/v1/session").status_code == 200
        with app.app_context():
            data = get_db().execute("SELECT data FROM http_sessions").fetchone()[0]
        assert set(json.loads(data)) == {
            "_permanent",
            "user_id",
            "auth_version",
            "csrf_token",
        }


@pytest.mark.parametrize(
    "role,customer",
    [("customer", None), ("agent", "c1"), ("unknown", None), ("customer", "absent")],
)
def test_account_creation_and_access_changes_share_mapping_validation(
    app, role, customer
):
    with app.app_context():
        with pytest.raises(ValueError) as creating:
            accounts.create_user("new-account", PASSWORD, role, customer)
        with pytest.raises(ValueError) as changing:
            accounts.change_access("a1", role, customer, [])
        assert str(creating.value) == str(changing.value)
        assert (
            get_db().execute("SELECT role FROM users WHERE user_id='a1'").fetchone()[0]
            == "agent"
        )


def test_password_update_uses_selected_id_even_if_username_changes(
    app, client, sign_in, monkeypatch
):
    assert sign_in(client).status_code == 200
    original_hash = accounts.generate_password_hash

    def rename_then_hash(password):
        with sqlite3.connect(app.config["DATABASE"]) as connection:
            connection.execute(
                "UPDATE users SET username='renamed-account' WHERE user_id='u1'"
            )
        return original_hash(password)

    monkeypatch.setattr(accounts, "generate_password_hash", rename_then_hash)
    result = app.test_cli_runner().invoke(
        args=["set-password", "customer-one"], input=PASSWORD + "\n" + PASSWORD + "\n"
    )
    assert result.exit_code == 0
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE user_id='u1'").fetchone()
        assert user["username"] == "renamed-account"
        assert check_password_hash(user["password_hash"], PASSWORD)
    assert client.get("/v1/session").status_code == 401
    assert sign_in(client, "renamed-account").status_code == 200
