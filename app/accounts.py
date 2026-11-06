"""Controlled account provisioning and access changes."""

import re
import sqlite3
from uuid import uuid4

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .clock import now
from .db import get_db

ROLES = ("customer", "agent", "administrator")
PERMISSIONS = ("reviewer", "release_authorizer")


def validate_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError("Choose a password containing 12 to 128 characters.")


def _validate_role_customer(role, customer_id):
    if role not in ROLES or (role == "customer") != bool(customer_id):
        raise ValueError("Only a customer account requires an existing customer ID.")
    if (
        customer_id
        and not get_db()
        .execute("SELECT 1 FROM customers WHERE customer_id = ?", (customer_id,))
        .fetchone()
    ):
        raise ValueError("Create the approved customer mapping first.")


def create_user(username, password, role, customer_id=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}", username):
        raise ValueError(
            "Use a username of 3 to 64 letters, digits, dots, dashes or underscores."
        )
    validate_password(password)
    _validate_role_customer(role, customer_id)
    user_id = str(uuid4())
    with get_db() as db:
        db.execute(
            "INSERT INTO users (user_id, username, password_hash, role, customer_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                generate_password_hash(password),
                role,
                customer_id,
                now(),
            ),
        )
    return user_id


def change_access(user_id, role, customer_id, permissions):
    _validate_role_customer(role, customer_id)
    permissions = set(permissions)
    if not permissions <= set(PERMISSIONS) or (role == "customer" and permissions):
        raise ValueError("Special permissions require a designated staff account.")
    db = get_db()
    with db:
        changed = db.execute(
            "UPDATE users SET role = ?, customer_id = ?, auth_version = auth_version + 1 "
            "WHERE user_id = ?",
            (role, customer_id, user_id),
        ).rowcount
        if not changed:
            raise ValueError("Account not found.")
        db.execute(
            "UPDATE active_sessions SET revoked = 1 WHERE user_id = ?", (user_id,)
        )
        db.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        db.executemany(
            "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
            [(user_id, p) for p in sorted(permissions)],
        )


@click.command("create-customer")
@click.argument("customer_id")
@click.option("--name", required=True, help="Fictional display name.")
@with_appcontext
def create_customer_command(customer_id, name):
    """Create an approved fictional customer mapping."""
    if not customer_id.strip() or len(customer_id) > 128 or not name.strip():
        raise click.ClickException("Supply a customer ID and a fictional name.")
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO customers (customer_id, display_name) VALUES (?, ?)",
                (customer_id, name),
            )
    except sqlite3.IntegrityError:
        raise click.ClickException("That customer mapping already exists.") from None
    click.echo("Customer mapping created.")


@click.command("create-user")
@click.argument("username")
@click.option("--role", type=click.Choice(ROLES), required=True)
@click.option("--customer-id", default=None)
@click.password_option(
    help="Choose the password at the prompt; do not put it in a command."
)
@with_appcontext
def create_user_command(username, role, customer_id, password):
    """Provision a controlled account with a hidden password prompt."""
    try:
        create_user(username, password, role, customer_id)
    except (ValueError, sqlite3.IntegrityError) as error:
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "That account cannot be created."
        )
        raise click.ClickException(message) from None
    click.echo("Account created.")


@click.command("set-password")
@click.argument("username")
@click.password_option()
@with_appcontext
def set_password_command(username, password):
    """Change an account password and revoke its existing sessions."""
    try:
        validate_password(password)
    except ValueError as error:
        raise click.ClickException(str(error)) from None
    with get_db() as db:
        user = db.execute(
            "SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        if user is None:
            raise click.ClickException("Account not found.")
        changed = db.execute(
            "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 "
            "WHERE user_id = ?",
            (generate_password_hash(password), user["user_id"]),
        ).rowcount
        db.execute(
            "UPDATE active_sessions SET revoked = 1 WHERE user_id = ?",
            (user["user_id"],),
        )
    if not changed:
        raise click.ClickException("Account not found.")
    click.echo("Password changed; existing sessions revoked.")


@click.command("set-access")
@click.argument("username")
@click.option("--role", type=click.Choice(ROLES), required=True)
@click.option("--customer-id", default=None)
@click.option("--permission", multiple=True, type=click.Choice(PERMISSIONS))
@with_appcontext
def set_access_command(username, role, customer_id, permission):
    """Replace role/permissions and revoke all previous sessions."""
    user = (
        get_db()
        .execute(
            "SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)
        )
        .fetchone()
    )
    if user is None:
        raise click.ClickException("Account not found.")
    try:
        change_access(user["user_id"], role, customer_id, permission)
    except (ValueError, sqlite3.IntegrityError):
        raise click.ClickException(
            "Invalid role, customer mapping or permissions."
        ) from None
    click.echo("Access updated; existing sessions revoked.")


@click.command("seed-demo")
@click.password_option(help="Choose a local demo password at the hidden prompt.")
@with_appcontext
def seed_demo_command(password):
    """Create four fictional accounts in an empty account store."""
    try:
        validate_password(password)
    except ValueError as error:
        raise click.ClickException(str(error)) from None
    db = get_db()
    if (
        db.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        or db.execute("SELECT 1 FROM customers LIMIT 1").fetchone()
    ):
        raise click.ClickException(
            "Accounts already exist. Use create-user or set-password."
        )
    rows = []
    for username, role, customer in [
        ("customer-demo", "customer", "demo-customer-1"),
        ("customer-two", "customer", "demo-customer-2"),
        ("agent-demo", "agent", None),
        ("admin-demo", "administrator", None),
    ]:
        rows.append(
            (
                str(uuid4()),
                username,
                generate_password_hash(password),
                role,
                customer,
                now(),
            )
        )
    with db:
        db.executemany(
            "INSERT INTO customers (customer_id, display_name) VALUES (?, ?)",
            [
                ("demo-customer-1", "Fictional Customer One"),
                ("demo-customer-2", "Fictional Customer Two"),
            ],
        )
        db.executemany(
            "INSERT INTO users (user_id, username, password_hash, role, customer_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
    click.echo("Created customer-demo, customer-two, agent-demo and admin-demo.")
    click.echo(
        "Use your chosen password. No special review/release permissions were granted."
    )


def init_app(app):
    for command in (
        create_customer_command,
        create_user_command,
        set_password_command,
        set_access_command,
        seed_demo_command,
    ):
        app.cli.add_command(command)
