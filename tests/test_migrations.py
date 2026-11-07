"""Atomic database upgrades and readiness of library-managed session storage."""

import sqlite3

import pytest

from app import create_app, db


def pending_versions(monkeypatch, tmp_path, *scripts):
    files = list(db.MIGRATIONS)
    previous = len(files)
    for version, script in enumerate(scripts, start=len(files) + 1):
        path = tmp_path / f"{version:03d}_test.sql"
        path.write_text(script)
        files.append(path)
    monkeypatch.setattr(db, "MIGRATIONS", tuple(files))
    monkeypatch.setattr(db, "SCHEMA_VERSION", len(files))
    return previous


def test_migration_noop_preserves_existing_accounts(app):
    result = app.test_cli_runner().invoke(args=["migrate-db"])
    assert (
        result.exit_code == 0
        and f"already at version {db.SCHEMA_VERSION}" in result.output
    )
    with app.app_context():
        assert db.get_db().execute("SELECT count(*) FROM users").fetchone()[0] == 5


def test_support_upgrade_preserves_version_one_records(tmp_path):
    database = tmp_path / "version-one.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(db.MIGRATIONS[0].read_text())
        connection.execute("PRAGMA user_version=1")
        connection.execute(
            "INSERT INTO customers VALUES ('legacy-customer','Fictional','active')"
        )
        connection.execute(
            "INSERT INTO submission_registrations (submission_id,customer_id,operation,state,registered_at,expires_at) VALUES ('legacy-id','legacy-customer','escalation','completed',1,1801)"
        )
        connection.execute(
            "INSERT INTO support_requests (request_id,submission_id,customer_id,content,reason,created_at) VALUES ('legacy-request','legacy-id','legacy-customer','Reviewed legacy content','human_requested',1)"
        )
        connection.execute(
            "INSERT INTO submission_receipts (submission_id,request_id,payload_fingerprint,committed_at) VALUES ('legacy-id','legacy-request','legacy-fingerprint',1)"
        )
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    assert app.test_client().get("/health").status_code == 503
    with app.app_context():
        assert db.migrate_db() == (1, 2)
        row = (
            db.get_db()
            .execute("SELECT content,note,inquiry_id FROM support_requests")
            .fetchone()
        )
        assert tuple(row) == ("Reviewed legacy content", None, None)
        receipt = (
            db.get_db()
            .execute("SELECT payload_fingerprint,reply_id FROM submission_receipts")
            .fetchone()
        )
        assert tuple(receipt) == ("legacy-fingerprint", None)
        assert db.get_db().execute("PRAGMA foreign_key_check").fetchall() == []
    assert app.test_client().get("/health").status_code == 200


def test_pending_versions_apply_in_order_and_keep_data(app, monkeypatch, tmp_path):
    base = pending_versions(
        monkeypatch,
        tmp_path,
        "ALTER TABLE customers ADD COLUMN plan TEXT NOT NULL DEFAULT 'starter';",
        "CREATE INDEX customer_plan ON customers(plan);",
    )
    with app.app_context():
        assert db.migrate_db() == (base, base + 2)
        connection = db.get_db()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == base + 2
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 5
        assert (
            connection.execute("SELECT plan FROM customers").fetchone()[0] == "starter"
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.migrate_db() == (base + 2, base + 2)


def test_failed_upgrade_rolls_back_all_pending_versions(app, monkeypatch, tmp_path):
    base = pending_versions(
        monkeypatch,
        tmp_path,
        "ALTER TABLE customers ADD COLUMN plan TEXT;",
        "CREATE TABLE temporary_change (id INTEGER); THIS IS INVALID SQL;",
    )
    with app.app_context():
        connection = db.get_db()
        with pytest.raises(sqlite3.Error):
            db.migrate_db()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == base
        assert "plan" not in {
            r[1] for r in connection.execute("PRAGMA table_info(customers)")
        }
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='temporary_change'"
            ).fetchone()
            is None
        )
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 5
        assert not connection.in_transaction


@pytest.mark.parametrize(
    "control", ["COMMIT;", "PRAGMA user_version = 99;", "SAVEPOINT unexpected;"]
)
def test_migrations_cannot_override_transaction_or_version(
    app, monkeypatch, tmp_path, control
):
    base = pending_versions(
        monkeypatch,
        tmp_path,
        "CREATE TABLE temporary_change (id INTEGER); " + control,
    )
    with app.app_context():
        connection = db.get_db()
        with pytest.raises(sqlite3.DatabaseError):
            db.migrate_db()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == base
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='temporary_change'"
            ).fetchone()
            is None
        )
        assert not connection.in_transaction


def test_newer_database_is_never_downgraded(app):
    with app.app_context():
        connection = db.get_db()
        connection.execute("PRAGMA user_version = 99")
        with pytest.raises(RuntimeError, match="newer"):
            db.migrate_db()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 99
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 5


def test_initialized_database_requires_explicit_upgrade(app, monkeypatch, tmp_path):
    base = pending_versions(
        monkeypatch, tmp_path, "CREATE TABLE future_feature (id INTEGER);"
    )
    with app.app_context():
        with pytest.raises(RuntimeError, match="migrate-db"):
            db.init_db()
    assert app.test_client().get("/health").status_code == 503
    result = app.test_cli_runner().invoke(args=["migrate-db"])
    assert (
        result.exit_code == 0 and f"from version {base} to {base + 1}" in result.output
    )
    assert app.test_client().get("/health").status_code == 200


def test_new_database_initializes_through_all_versions(monkeypatch, tmp_path):
    base = pending_versions(
        monkeypatch, tmp_path, "CREATE TABLE future_feature (id INTEGER);"
    )
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "fresh.sqlite3")})
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    with app.app_context():
        assert db.get_db().execute("PRAGMA user_version").fetchone()[0] == base + 1
        assert db.is_schema_ready()


def test_migrations_do_not_commit_callers_pending_work(app):
    with app.app_context():
        connection = db.get_db()
        connection.execute(
            "INSERT INTO customers VALUES ('pending', 'Uncommitted', 'active')"
        )
        with pytest.raises(RuntimeError, match="current transaction"):
            db.migrate_db()
        assert connection.in_transaction
        connection.rollback()
        assert (
            connection.execute(
                "SELECT 1 FROM customers WHERE customer_id='pending'"
            ).fetchone()
            is None
        )


def test_sql_literals_comments_and_triggers_survive_statement_splitting(
    app, monkeypatch, tmp_path
):
    pending_versions(
        monkeypatch,
        tmp_path,
        """
        -- A comment with a semicolon; is not a statement.
        CREATE TABLE migration_notes (content TEXT); INSERT INTO migration_notes VALUES ('one;two');
        CREATE TRIGGER customer_note AFTER INSERT ON customers BEGIN
            INSERT INTO migration_notes VALUES (new.customer_id || ';created');
        END;
        -- Trailing comments are allowed.
    """,
    )
    with app.app_context():
        db.migrate_db()
        with db.get_db() as connection:
            connection.execute(
                "INSERT INTO customers VALUES ('new', 'Fictional', 'active')"
            )
        assert [
            r[0] for r in connection.execute("SELECT content FROM migration_notes")
        ] == ["one;two", "new;created"]


@pytest.mark.parametrize("incomplete", [False, True])
@pytest.mark.parametrize("signed_in", [False, True])
def test_health_detects_missing_or_incomplete_http_session_storage(
    app, client, sign_in, incomplete, signed_in
):
    if signed_in:
        assert sign_in(client).status_code == 200
    with app.app_context():
        with db.get_db() as connection:
            connection.execute("DROP TABLE http_sessions")
            if incomplete:
                connection.execute(
                    "CREATE TABLE http_sessions (id INTEGER PRIMARY KEY)"
                )
        assert not db.is_schema_ready()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "http_sessions" not in response.text
