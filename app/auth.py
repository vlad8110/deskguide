"""Login, CSRF, throttling and revocable server-side session validation."""

import hashlib
import secrets
from typing import cast

from flask import Blueprint, current_app, g, jsonify, request, session
from flask_session.base import ServerSideSession, ServerSideSessionInterface
from werkzeug.security import check_password_hash

from .access import AccessContext, current_access
from .clock import now, timestamp
from .db import get_db
from .errors import CONTRACT_VERSION, ApiError

bp = Blueprint("auth", __name__, url_prefix="/v1/session")


def _session_record(user_id):
    return (
        get_db()
        .execute(
            "SELECT * FROM active_sessions WHERE session_hash = ? AND user_id = ?",
            (session_hash(), user_id),
        )
        .fetchone()
    )


def _session_is_valid(user, record, current):
    if record is None or user is None:
        return False
    issued, last_seen = record["issued_at"], record["last_seen"]
    return (
        record["revoked"] == 0
        and user["active"] == 1
        and record["auth_version"] == user["auth_version"]
        and session.get("auth_version") == user["auth_version"]
        and isinstance(issued, int)
        and isinstance(last_seen, int)
        and issued <= current
        and last_seen <= current
        and current < issued + current_app.config["ABSOLUTE_SESSION_SECONDS"]
        and current < record["expires_at"]
        and current < last_seen + current_app.config["IDLE_SESSION_SECONDS"]
        and (user["role"] != "customer" or user["customer_id"] is not None)
    )


def load_access():
    g.access = None
    g.account = None
    if "user_id" not in session:
        return
    user = (
        get_db()
        .execute("SELECT * FROM users WHERE user_id = ?", (session["user_id"],))
        .fetchone()
    )
    current = now()
    record = _session_record(session["user_id"])
    if not _session_is_valid(user, record, current):
        session.clear()
        return
    issued, last_seen = record["issued_at"], record["last_seen"]
    if current - last_seen >= current_app.config["SESSION_ACTIVITY_REFRESH_SECONDS"]:
        with get_db() as connection:
            changed = connection.execute(
                "UPDATE active_sessions SET last_seen = ? "
                "WHERE session_hash = ? AND revoked = 0 AND last_seen = ?",
                (current, session_hash(), last_seen),
            ).rowcount
        if changed:
            last_seen = current
            # Refresh storage/cookie expiry without duplicating registry metadata.
            session.modified = True
        else:
            # Another request may have refreshed or revoked this session meanwhile.
            record = _session_record(session["user_id"])
            if not _session_is_valid(user, record, current):
                session.clear()
                return
            last_seen = record["last_seen"]
    permissions = frozenset(
        row[0]
        for row in get_db().execute(
            "SELECT permission FROM user_permissions WHERE user_id = ?",
            (user["user_id"],),
        )
    )
    g.access = AccessContext(
        user["user_id"],
        user["role"],
        user["customer_id"],
        permissions,
        g.correlation_id,
    )
    g.account = user
    g.session_expires = min(
        record["expires_at"], issued + current_app.config["ABSOLUTE_SESSION_SECONDS"]
    )
    g.session_idle_expires = min(
        g.session_expires, last_seen + current_app.config["IDLE_SESSION_SECONDS"]
    )


def session_hash():
    server_session = cast(ServerSideSession, session)
    # Flask-Session assigns an ID when it opens the request session.
    session_id = cast(str, server_session.sid)
    return hashlib.sha256(session_id.encode()).hexdigest()


def enforce_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if request.endpoint != "auth.login":
        current_access()
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token", "")
    if (
        not isinstance(expected, str)
        or len(supplied) > 256
        or not secrets.compare_digest(
            expected.encode("utf-8"), supplied.encode("utf-8")
        )
    ):
        raise ApiError(403, "CSRF_FAILED", "Refresh the page and try again.")
    if request.endpoint == "auth.login" and g.access is None:
        issued = session.get("login_token_issued_at", 0)
        if now() >= issued + 600:
            raise ApiError(403, "CSRF_FAILED", "Refresh the page and try again.")


@bp.get("/login-token")
def login_token():
    if "csrf_token" not in session or (
        g.access is None and now() >= session.get("login_token_issued_at", 0) + 600
    ):
        session["csrf_token"] = secrets.token_urlsafe(32)
        session["login_token_issued_at"] = now()
    if not session.permanent:
        session.permanent = True
    return jsonify(
        csrf_token=session["csrf_token"],
        contract_version=CONTRACT_VERSION,
        correlation_id=g.correlation_id,
    )


def login_buckets(username):
    def digest(text):
        return hashlib.sha256(text.encode()).hexdigest()

    return [
        ("user:" + digest(username.casefold()), current_app.config["LOGIN_USER_LIMIT"]),
        (
            "address:" + digest(request.remote_addr or "local"),
            current_app.config["LOGIN_ADDRESS_LIMIT"],
        ),
    ]


def _check_login_limits(connection, buckets, current):
    for key, limit in buckets:
        row = connection.execute(
            "SELECT failures, reset_at FROM login_attempts WHERE bucket = ?", (key,)
        ).fetchone()
        if row and row["reset_at"] > current and row["failures"] >= limit:
            raise ApiError(
                429,
                "RATE_LIMITED",
                "Too many sign-in attempts. Try again later.",
                retryable=True,
                retry_after=row["reset_at"] - current,
            )


@bp.post("/login")
def login():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"username", "password"}:
        raise ApiError(
            400, "VALIDATION_FAILED", "Provide only a username and password."
        )
    username, password = payload["username"], payload["password"]
    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not (1 <= len(username) <= 64 and 1 <= len(password) <= 128)
    ):
        raise ApiError(
            400, "VALIDATION_FAILED", "Provide a valid username and password."
        )
    buckets = login_buckets(username)
    db = get_db()
    current = now()
    _check_login_limits(db, buckets, current)
    user = db.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
    ).fetchone()
    encoded = (
        user["password_hash"] if user else current_app.config["DUMMY_PASSWORD_HASH"]
    )
    password_ok = check_password_hash(encoded, password)
    authenticated = user is not None and user["active"] and password_ok
    with db:
        # Serialize only the decision/counter writes, not password hashing.
        db.execute("BEGIN IMMEDIATE")
        _check_login_limits(db, buckets, current)
        if authenticated:
            db.execute("DELETE FROM login_attempts WHERE bucket = ?", (buckets[0][0],))
            db.execute(
                "UPDATE active_sessions SET revoked = 1 WHERE session_hash = ?",
                (session_hash(),),
            )
        else:
            db.execute("DELETE FROM login_attempts WHERE reset_at <= ?", (current,))
            for key, _limit in buckets:
                db.execute(
                    "INSERT INTO login_attempts (bucket, failures, reset_at) VALUES (?, 1, ?) "
                    "ON CONFLICT(bucket) DO UPDATE SET failures = failures + 1",
                    (key, current + current_app.config["LOGIN_WINDOW_SECONDS"]),
                )
    if not authenticated:
        raise ApiError(401, "UNAUTHENTICATED", "Username or password is incorrect.")
    # Regenerate while the old session is nonempty; clearing first can skip rotation.
    cast(ServerSideSessionInterface, current_app.session_interface).regenerate(
        cast(ServerSideSession, session)
    )
    session.clear()
    session.permanent = True
    session.update(
        user_id=user["user_id"],
        auth_version=user["auth_version"],
        csrf_token=secrets.token_urlsafe(32),
    )
    with db:
        db.execute(
            "INSERT INTO active_sessions "
            "(session_hash, user_id, auth_version, issued_at, last_seen, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_hash(),
                user["user_id"],
                user["auth_version"],
                current,
                current,
                current + current_app.config["ABSOLUTE_SESSION_SECONDS"],
            ),
        )
    return jsonify(
        role=user["role"],
        contract_version=CONTRACT_VERSION,
        correlation_id=g.correlation_id,
    )


@bp.get("")
def session_status():
    context = current_access()
    absolute = g.session_expires
    idle = g.session_idle_expires
    return jsonify(
        role=context.role,
        expires_at=timestamp(absolute),
        idle_expires_at=timestamp(idle),
        csrf_token=session["csrf_token"],
        contract_version=CONTRACT_VERSION,
        correlation_id=g.correlation_id,
    )


@bp.post("/logout")
def logout():
    current_access()
    with get_db() as connection:
        connection.execute(
            "UPDATE active_sessions SET revoked = 1 WHERE session_hash = ?",
            (session_hash(),),
        )
    session.clear()
    return "", 204
