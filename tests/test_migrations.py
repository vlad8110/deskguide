"""Atomic database upgrades and readiness of library-managed session storage."""

import sqlite3
from uuid import uuid4

import pytest
from werkzeug.security import generate_password_hash

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
        assert db.migrate_db() == (1, db.SCHEMA_VERSION)
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


def test_agent_upgrade_preserves_version_two_messages_and_receipts(tmp_path):
    database = tmp_path / "version-two.sqlite3"
    with sqlite3.connect(database) as connection:
        for migration in db.MIGRATIONS[:2]:
            connection.executescript(migration.read_text())
        connection.execute("PRAGMA user_version=2")
        connection.execute(
            "INSERT INTO customers VALUES ('old-customer','Fictional','active')"
        )
        connection.execute(
            "INSERT INTO users VALUES ('old-user','old-user','fictional-hash','customer','old-customer',1,1,1)"
        )
        connection.execute(
            "INSERT INTO submission_registrations (submission_id,customer_id,operation,state,registered_at,expires_at) VALUES ('old-submit','old-customer','escalation','completed',1,1801)"
        )
        connection.execute(
            "INSERT INTO support_requests (request_id,submission_id,customer_id,content,note,reason,created_at) VALUES ('old-request','old-submit','old-customer','Reviewed support','Reviewed note','human_requested',1)"
        )
        connection.execute(
            "INSERT INTO submission_registrations (submission_id,customer_id,operation,parent_request_id,state,registered_at,expires_at) VALUES ('old-reply-submit','old-customer','reply','old-request','completed',2,1802)"
        )
        connection.execute(
            "INSERT INTO support_replies VALUES ('old-reply','old-request','old-reply-submit','old-user','Reviewed reply',2)"
        )
        connection.execute(
            "INSERT INTO submission_receipts VALUES ('old-reply-submit','old-request','comparison-value',2,'old-reply')"
        )
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    with app.app_context():
        assert db.migrate_db() == (2, db.SCHEMA_VERSION)
        connection = db.get_db()
        assert tuple(
            connection.execute("SELECT content,note FROM support_requests").fetchone()
        ) == ("Reviewed support", "Reviewed note")
        assert tuple(
            connection.execute(
                "SELECT content,request_version FROM support_replies"
            ).fetchone()
        ) == ("Reviewed reply", None)
        assert (
            connection.execute("SELECT reply_id FROM submission_receipts").fetchone()[0]
            == "old-reply"
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM support_state_events").fetchone()[
                0
            ]
            == 0
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


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


def test_feedback_upgrade_preserves_legacy_rows_and_accepts_a_rating(tmp_path, sign_in):
    database = tmp_path / "version-three.sqlite3"
    inquiry_id = str(uuid4())
    password = "Fictional-feedback-passphrase-12!"
    with sqlite3.connect(database) as connection:
        for migration in db.MIGRATIONS[:3]:
            connection.executescript(migration.read_text())
        connection.execute("PRAGMA user_version=3")
        connection.execute(
            "INSERT INTO customers (customer_id, display_name) VALUES ('c', 'Demo')"
        )
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash, role, customer_id, created_at) "
            "VALUES ('u','legacy-customer',?,'customer','c',1)",
            (generate_password_hash(password),),
        )
        connection.execute(
            "INSERT INTO inquiries (inquiry_id, customer_id, route, outcome, created_at, expires_at) "
            "VALUES (?, 'c', 'ai', 'temporarily_unavailable', 1, 2000)",
            (inquiry_id,),
        )
        connection.executemany(
            "INSERT INTO feedback VALUES (?, ?, 'c', ?, 'Demo comment', 1)",
            [("f1", inquiry_id, "unclear"), ("f2", inquiry_id, "other")],
        )
    app = create_app(
        {"TESTING": True, "DATABASE": str(database), "TIME_PROVIDER": lambda: 1000}
    )
    with app.app_context():
        assert db.migrate_db() == (3, 4)

    client = app.test_client()
    assert sign_in(client, "legacy-customer", password).status_code == 200
    token = client.get("/v1/session").json["csrf_token"]
    request = {
        "json": {"inquiry_id": inquiry_id, "rating": "helpful"},
        "headers": {"X-CSRF-Token": token},
    }
    saved = client.post("/v1/feedback", **request)
    assert saved.status_code == 201
    assert client.post("/v1/feedback", **request).status_code == 409

    with app.app_context():
        connection = db.get_db()
        rows = connection.execute(
            "SELECT feedback_id, rating, category, comment, state FROM feedback "
            "ORDER BY created_at, feedback_id"
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            ("f1", None, "unclear", "Demo comment", "legacy"),
            ("f2", None, "other", "Demo comment", "legacy"),
            (saved.json["feedback_id"], "helpful", None, None, "pending_review"),
        ]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
