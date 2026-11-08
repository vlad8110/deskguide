"""Confirmed support saves, scoped submission receipts and customer replies."""

import hashlib
import json
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from uuid import UUID, uuid4

import click
from flask import Blueprint, current_app, g, jsonify, request
from flask.cli import with_appcontext

from .access import current_access, require_roles
from .clock import now, timestamp
from .db import get_db
from .errors import CONTRACT_VERSION, ApiError

bp = Blueprint("support", __name__, url_prefix="/v1/escalations")
REASONS = (
    "insufficient_evidence",
    "human_requested",
    "validation_failed",
    "provider_failure",
    "service_unavailable",
    "action_required",
)
RETENTION = 30 * 86400


def _envelope(**fields):
    return jsonify(
        contract_version=CONTRACT_VERSION, correlation_id=g.correlation_id, **fields
    )


def _invalid(message):
    raise ApiError(400, "VALIDATION_FAILED", message)


def _uuid(value, field):
    try:
        if not isinstance(value, str) or len(value) != 36:
            raise ValueError
        parsed = UUID(value)
        if parsed.version != 4 or str(parsed) != value:
            raise ValueError
    except ValueError:
        _invalid(f"Provide a valid {field}.")
    return value


def _text(value, field, limit, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or any(
        unicodedata.category(c) in {"Cc", "Cs"} and c not in "\n\r\t" for c in value
    ):
        _invalid(f"Provide plain text for {field}.")
    value = unicodedata.normalize("NFC", value).strip()
    if len(value) > limit or (not optional and not value):
        _invalid(
            f"{field} must contain {'0' if optional else '1'} to {limit} characters."
        )
    return value


def _payload(required, optional=()):
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or not set(required) <= value.keys():
        _invalid("Provide all required submission fields.")
    if value.keys() - set(required) - set(optional):
        _invalid("Remove unrecognized submission fields.")
    return value


def _not_found():
    raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")


def _conflict(message="This request changed. Please reload and try again."):
    raise ApiError(409, "CONFLICT", message)


@contextmanager
def _transaction(*, saving=False, agent_update=False):
    connection = get_db()
    committing = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        committing = True
        connection.commit()
    except Exception as error:
        rollback_failed = False
        try:
            connection.rollback()
        except sqlite3.Error:
            rollback_failed = True
        if isinstance(error, ApiError):
            raise
        if not isinstance(error, sqlite3.Error) and not (
            (saving or agent_update) and committing
        ):
            raise
        uncertain = saving and (committing or rollback_failed)
        category = "SAVE_OUTCOME_UNCERTAIN" if uncertain else "DEPENDENCY_UNAVAILABLE"
        current_app.logger.warning(
            "support_storage_failure category=%s correlation_id=%s",
            category,
            getattr(g, "correlation_id", "unavailable"),
        )
        if uncertain:
            message = "We could not confirm whether this was saved. Check its status using the same submission ID."
        elif agent_update and (committing or rollback_failed):
            message = "We could not confirm this update. Reload the request before trying again."
        elif saving:
            message = (
                "The request was not saved. Please retry with the same submission ID."
            )
        else:
            message = "Support is temporarily unavailable. Please try again shortly."
        raise ApiError(503, category, message, retryable=True, retry_after=1) from None


def _owned_request(connection, request_id, customer):
    row = connection.execute(
        "SELECT * FROM support_requests WHERE request_id=? AND customer_id=? "
        "AND (resolved_at IS NULL OR resolved_at>?)",
        (request_id, customer, now() - RETENTION),
    ).fetchone()
    if row is None:
        _not_found()
    return row


def record_state_event(connection, row, to_state, operation, *, reason_given=False):
    context = current_access()
    connection.execute(
        "INSERT INTO support_state_events "
        "(event_id,request_id,actor_id,actor_role,operation,from_state,to_state,version,reason_given,correlation_id,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            str(uuid4()),
            row["request_id"],
            context.subject_id,
            context.role,
            operation,
            row["state"],
            to_state,
            row["version"] + 1,
            int(reason_given),
            context.correlation_id,
            now(),
        ),
    )


def request_details(connection, row, *, agent=False):
    """Return reviewed request text and messages only after caller authorization."""
    result = dict(
        request_id=row["request_id"],
        state=row["state"],
        version=row["version"],
        content=row["content"],
        note=row["note"],
        reason=row["reason"],
        created_at=timestamp(row["created_at"]),
        messages=[],
    )
    messages = [
        dict(
            message_id=r["reply_id"],
            kind="customer_reply",
            content=r["content"],
            created_at=timestamp(r["created_at"]),
            version=r["request_version"],
        )
        for r in connection.execute(
            "SELECT reply_id,content,created_at,request_version FROM support_replies WHERE request_id=?",
            (row["request_id"],),
        )
    ]
    sql = "SELECT message_id,kind,content,created_at,request_version FROM support_agent_messages WHERE request_id=?"
    if not agent:
        sql += " AND kind='message_to_customer'"
    messages.extend(
        dict(
            message_id=r["message_id"],
            kind=r["kind"],
            content=r["content"],
            created_at=timestamp(r["created_at"]),
            version=r["request_version"],
        )
        for r in connection.execute(sql, (row["request_id"],))
    )
    result["messages"] = sorted(
        messages, key=lambda m: (m["created_at"], m["version"] or 0, m["message_id"])
    )
    return result


def _registration(connection, submission_id, customer, *, operation=None, parent=None):
    row = connection.execute(
        "SELECT * FROM submission_registrations WHERE submission_id=? AND customer_id=?",
        (submission_id, customer),
    ).fetchone()
    if (
        row is None
        or (operation is not None and row["operation"] != operation)
        or (parent is not None and row["parent_request_id"] != parent)
    ):
        _not_found()
    return row


def _receipt(connection, registration):
    receipt = connection.execute(
        "SELECT * FROM submission_receipts WHERE submission_id=?",
        (registration["submission_id"],),
    ).fetchone()
    if registration["state"] == "completed" and receipt is None:
        # An incomplete retained identity must never be interpreted as a fresh save.
        _not_found()
    return receipt


def _check_unused(registration):
    if registration["state"] == "expired" or registration["expires_at"] <= now():
        raise ApiError(
            410,
            "SUBMISSION_ID_EXPIRED",
            "This form timed out before it was sent. Start a new submission deliberately.",
        )
    if registration["state"] != "unused":
        _not_found()


def _fingerprint(payload, customer, operation, parent, salt):
    canonical = json.dumps(
        [customer, operation, parent, payload],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256((salt + ":" + canonical).encode()).hexdigest()


def _record_receipt(connection, registration, payload, request_id, *, reply_id=None):
    salt = secrets.token_hex(32)
    digest = _fingerprint(
        payload,
        registration["customer_id"],
        registration["operation"],
        registration["parent_request_id"],
        salt,
    )
    connection.execute(
        "INSERT INTO submission_receipts (submission_id,request_id,payload_fingerprint,committed_at,reply_id) VALUES (?,?,?,?,?)",
        (
            registration["submission_id"],
            request_id,
            f"sha256:{salt}:{digest}",
            now(),
            reply_id,
        ),
    )
    connection.execute(
        "UPDATE submission_registrations SET state='completed' WHERE submission_id=?",
        (registration["submission_id"],),
    )


def _same_payload(receipt, registration, payload):
    parts = receipt["payload_fingerprint"].split(":")
    if len(parts) != 3 or parts[0] != "sha256":
        _conflict(
            "This receipt cannot be compared. Keep this submission ID and contact support."
        )
    expected = _fingerprint(
        payload,
        registration["customer_id"],
        registration["operation"],
        registration["parent_request_id"],
        parts[1],
    )
    if not secrets.compare_digest(expected, parts[2]):
        _conflict(
            "This submission was already saved with different content. Start a new request to send something new."
        )


def _capacity(connection):
    total = connection.execute(
        "SELECT COUNT(*) FROM support_requests WHERE state!='resolved'"
    ).fetchone()[0]
    if total >= current_app.config["SUPPORT_MAX_OPEN_REQUESTS"]:
        raise ApiError(
            503,
            "SERVICE_BUSY",
            "Support is busy. Please try again shortly.",
            retryable=True,
            retry_after=1,
        )


def _register(operation, parent=None):
    customer = current_access().customer_scope
    with _transaction() as connection:
        if parent:
            row = _owned_request(connection, parent, customer)
            if row["state"] != "waiting_for_customer":
                _conflict("This request is not waiting for a customer reply.")
        else:
            _capacity(connection)
        pending = connection.execute(
            "SELECT expires_at FROM submission_registrations WHERE customer_id=? AND state='unused' AND expires_at>?",
            (customer, now()),
        ).fetchall()
        if len(pending) >= 3:
            raise ApiError(
                429,
                "RATE_LIMITED",
                "You have too many pending submissions. Please finish one or wait for it to expire.",
                retryable=True,
                retry_after=max(1, min(r[0] for r in pending) - now()),
            )
        submission_id = str(uuid4())
        expires = now() + 1800
        connection.execute(
            "INSERT INTO submission_registrations (submission_id,customer_id,operation,parent_request_id,registered_at,expires_at) VALUES (?,?,?,?,?,?)",
            (submission_id, customer, operation, parent, now(), expires),
        )
    result = dict(
        submission_id=submission_id,
        operation=operation,
        registration_state="unused",
        expires_at=timestamp(expires),
    )
    if parent:
        result["request_id"] = parent
    return _envelope(**result), 201


@bp.post("/submission-ids")
@require_roles("customer")
def register_request():
    payload = _payload(("operation",))
    if payload["operation"] != "escalation":
        _invalid("Choose the escalation operation.")
    return _register("escalation")


@bp.post("/<request_id>/reply-ids")
@require_roles("customer")
def register_reply(request_id):
    _uuid(request_id, "request_id")
    payload = _payload(("operation",))
    if payload["operation"] != "reply":
        _invalid("Choose the reply operation.")
    return _register("reply", request_id)


def _saved_request(row, submission_id):
    return _envelope(
        request_id=row["request_id"],
        submission_id=submission_id,
        state=row["state"],
        created_at=timestamp(row["created_at"]),
        acknowledgement="Your request has been saved.",
    )


@bp.post("")
@require_roles("customer")
def submit_request():
    payload = _payload(
        ("submission_id", "reason", "content", "consent_to_share"),
        ("inquiry_id", "note"),
    )
    submission_id = _uuid(payload["submission_id"], "submission_id")
    reason = payload["reason"]
    if reason not in REASONS:
        _invalid("Choose a supported reason.")
    if payload["consent_to_share"] is not True:
        _invalid("consent_to_share must be true before sending to support.")
    inquiry_id = payload.get("inquiry_id")
    if inquiry_id is not None:
        _uuid(inquiry_id, "inquiry_id")
    canonical = dict(
        reason=reason,
        inquiry_id=inquiry_id,
        content=_text(payload["content"], "content", 1000),
        note=_text(payload.get("note"), "note", 2000, optional=True),
        consent_to_share=True,
    )
    customer = current_access().customer_scope
    with _transaction(saving=True) as connection:
        registration = _registration(
            connection, submission_id, customer, operation="escalation"
        )
        receipt = _receipt(connection, registration)
        if receipt:
            row = _owned_request(connection, receipt["request_id"], customer)
            _same_payload(receipt, registration, canonical)
            status = 200
        else:
            _check_unused(registration)
            if (
                inquiry_id is not None
                and connection.execute(
                    "SELECT 1 FROM inquiries WHERE inquiry_id=? AND customer_id=? AND expires_at>?",
                    (inquiry_id, customer, now()),
                ).fetchone()
                is None
            ):
                raise ApiError(403, "FORBIDDEN", "This inquiry is unavailable.")
            recent = connection.execute(
                "SELECT created_at FROM support_requests WHERE customer_id=? AND created_at>?",
                (customer, now() - 3600),
            ).fetchall()
            if len(recent) >= 5:
                raise ApiError(
                    429,
                    "RATE_LIMITED",
                    "Please wait before sending another support request.",
                    retryable=True,
                    retry_after=max(1, min(r[0] for r in recent) + 3600 - now()),
                )
            _capacity(connection)
            request_id = str(uuid4())
            connection.execute(
                "INSERT INTO support_requests (request_id,submission_id,customer_id,content,reason,note,inquiry_id,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    submission_id,
                    customer,
                    canonical["content"],
                    reason,
                    canonical["note"],
                    inquiry_id,
                    now(),
                ),
            )
            _record_receipt(connection, registration, canonical, request_id)
            row = _owned_request(connection, request_id, customer)
            status = 201
    return _saved_request(row, submission_id), status


@bp.get("/<submission_id>")
@require_roles("customer")
def submission_status(submission_id):
    _uuid(submission_id, "submission_id")
    customer = current_access().customer_scope
    # One read transaction keeps registration/receipt/request observations consistent.
    connection = get_db()
    try:
        connection.execute("BEGIN")
        registration = _registration(connection, submission_id, customer)
        receipt = _receipt(connection, registration)
        row = None
        if receipt:
            row = _owned_request(connection, receipt["request_id"], customer)
        elif registration["parent_request_id"]:
            _owned_request(connection, registration["parent_request_id"], customer)
        state = (
            "completed"
            if receipt
            else (
                "expired"
                if registration["expires_at"] <= now()
                or registration["state"] == "expired"
                else "unused"
            )
        )
        result = dict(
            submission_id=submission_id,
            operation=registration["operation"],
            registration_state=state,
            saved=receipt is not None,
            request_id=row["request_id"] if row else registration["parent_request_id"],
            state=row["state"] if row else None,
            created_at=timestamp(receipt["committed_at"]) if receipt else None,
            expires_at=None if receipt else timestamp(registration["expires_at"]),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return _envelope(**result)


@bp.post("/<request_id>/replies")
@require_roles("customer")
def submit_reply(request_id):
    _uuid(request_id, "request_id")
    payload = _payload(("submission_id", "message", "expected_version"))
    submission_id = _uuid(payload["submission_id"], "submission_id")
    version = payload["expected_version"]
    if type(version) is not int or not 1 <= version <= 2147483647:
        _invalid("Provide a positive expected_version.")
    canonical = dict(
        message=_text(payload["message"], "message", 2000), expected_version=version
    )
    customer = current_access().customer_scope
    with _transaction(saving=True) as connection:
        registration = _registration(
            connection, submission_id, customer, operation="reply", parent=request_id
        )
        row = _owned_request(connection, request_id, customer)
        receipt = _receipt(connection, registration)
        if receipt:
            _same_payload(receipt, registration, canonical)
            reply_id = receipt["reply_id"]
            if reply_id is None:
                _not_found()
            status = 200
        else:
            _check_unused(registration)
            if row["state"] != "waiting_for_customer" or row["version"] != version:
                _conflict(
                    "This request is no longer waiting for this reply. Reload its status."
                )
            reply_id = str(uuid4())
            connection.execute(
                "INSERT INTO support_replies (reply_id,request_id,submission_id,author_id,content,created_at,request_version) VALUES (?,?,?,?,?,?,?)",
                (
                    reply_id,
                    request_id,
                    submission_id,
                    current_access().subject_id,
                    canonical["message"],
                    now(),
                    row["version"] + 1,
                ),
            )
            connection.execute(
                "UPDATE support_requests SET state='in_review',version=version+1 WHERE request_id=?",
                (request_id,),
            )
            record_state_event(connection, row, "in_review", "customer_reply")
            _record_receipt(
                connection, registration, canonical, request_id, reply_id=reply_id
            )
            row = _owned_request(connection, request_id, customer)
            status = 201
    return _envelope(
        reply_id=reply_id,
        request_id=request_id,
        state=row["state"],
        version=row["version"],
    ), status


@bp.get("/requests/<request_id>")
@require_roles("customer")
def customer_request_details(request_id):
    _uuid(request_id, "request_id")
    connection = get_db()
    try:
        connection.execute("BEGIN")
        row = _owned_request(connection, request_id, current_access().customer_scope)
        result = request_details(connection, row)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return _envelope(**result)


@click.command("cleanup-support")
@with_appcontext
def cleanup_support_command():
    """Purge expired unused IDs and resolved support after its retention period."""
    with _transaction() as connection:
        expired = connection.execute(
            "SELECT request_id,submission_id FROM support_requests WHERE state='resolved' AND resolved_at<=?",
            (now() - RETENTION,),
        ).fetchall()
        for row in expired:
            rid = row["request_id"]
            connection.execute(
                "DELETE FROM submission_receipts WHERE request_id=?", (rid,)
            )
            connection.execute("DELETE FROM support_replies WHERE request_id=?", (rid,))
            connection.execute(
                "DELETE FROM submission_registrations WHERE parent_request_id=?", (rid,)
            )
            connection.execute(
                "DELETE FROM support_requests WHERE request_id=?", (rid,)
            )
            connection.execute(
                "DELETE FROM submission_registrations WHERE submission_id=?",
                (row["submission_id"],),
            )
        unused = connection.execute(
            "DELETE FROM submission_registrations WHERE state!='completed' AND expires_at<=? AND NOT EXISTS (SELECT 1 FROM support_requests r WHERE r.submission_id=submission_registrations.submission_id)",
            (now(),),
        ).rowcount
    click.echo(
        f"Removed {len(expired)} expired resolved requests and {unused} unused registrations."
    )


def init_app(app):
    app.config.setdefault("SUPPORT_MAX_OPEN_REQUESTS", 100)
    app.register_blueprint(bp)
    app.cli.add_command(cleanup_support_command)
