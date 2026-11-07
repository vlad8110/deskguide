"""SQLite initialization, connections and expired authentication cleanup."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext

from .clock import now

# Append each future version's SQL file here; never edit an applied migration.
MIGRATIONS = (
    Path(__file__).with_name("schema.sql"),
    Path(__file__).with_name("migrations") / "002_support_details.sql",
)
SCHEMA_VERSION = len(MIGRATIONS)


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, SCHEMA_VERSION):
        raise RuntimeError(
            "Database version requires migrate-db or a matching application version; "
            "no data was changed."
        )
    if version == 0:
        previous, _current = migrate_db()
        return previous == 0
    return False


def _run_migration(connection, script):
    """Execute complete SQL statements without executescript's implicit commit."""

    def keep_runner_in_control(action, _first, _second, _database, _source):
        if action in {
            sqlite3.SQLITE_TRANSACTION,
            sqlite3.SQLITE_SAVEPOINT,
            sqlite3.SQLITE_PRAGMA,
        }:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(keep_runner_in_control)
    try:
        statement = ""
        for character in script:
            statement += character
            if character == ";" and sqlite3.complete_statement(statement):
                connection.execute(statement)
                statement = ""
        if statement.strip():
            connection.execute(statement)
    finally:
        connection.set_authorizer(None)


def migrate_db():
    """Apply pending versions atomically; reject downgrades and roll back failures."""
    connection = get_db()
    if connection.in_transaction:
        raise RuntimeError("Finish the current transaction before migrating.")
    connection.execute("BEGIN IMMEDIATE")
    try:
        previous = connection.execute("PRAGMA user_version").fetchone()[0]
        if previous > SCHEMA_VERSION:
            raise RuntimeError(
                "Database is newer than this application; no data was changed."
            )
        for version in range(previous + 1, SCHEMA_VERSION + 1):
            _run_migration(connection, MIGRATIONS[version - 1].read_text())
            connection.execute(f"PRAGMA user_version = {version}")
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise RuntimeError("Migration failed the foreign-key check.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return previous, SCHEMA_VERSION


def is_schema_ready():
    connection = get_db()
    if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        return False
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(http_sessions)")
    }
    return {"id", "session_id", "data", "expiry"} <= columns


@click.command("migrate-db")
@with_appcontext
def migrate_db_command():
    """Upgrade the existing database through all pending numbered versions."""
    try:
        previous, current = migrate_db()
    except (OSError, RuntimeError, sqlite3.Error) as error:
        raise click.ClickException(str(error)) from None
    if previous == current:
        click.echo(f"Database is already at version {current}.")
    else:
        click.echo(f"Database migrated from version {previous} to {current}.")


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize a new schema without dropping existing records."""
    created = init_db()
    click.echo(
        "Database initialized." if created else "Database is already initialized."
    )


@click.command("cleanup-auth")
@with_appcontext
def cleanup_auth_command():
    """Remove expired app/HTTP sessions and counters; retain live tombstones."""
    # Flask-Session stores naive UTC expiry, independently of the auth test clock.
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    with get_db() as connection:
        sessions = connection.execute(
            "DELETE FROM active_sessions WHERE expires_at <= ?", (now(),)
        ).rowcount
        buckets = connection.execute(
            "DELETE FROM login_attempts WHERE reset_at <= ?", (now(),)
        ).rowcount
        http_sessions = connection.execute(
            "DELETE FROM http_sessions WHERE expiry IS NULL OR expiry <= ?",
            (utc_now,),
        ).rowcount
    click.echo(
        f"Removed {sessions} expired auth records, {http_sessions} expired HTTP sessions "
        f"and {buckets} expired login counters."
    )


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
    app.cli.add_command(cleanup_auth_command)
