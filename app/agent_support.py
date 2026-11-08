"""Agent-scoped queues, atomic claims and version-checked support transitions."""

from uuid import uuid4

from flask import Blueprint, current_app, request
from itsdangerous import BadSignature, URLSafeSerializer

from .access import current_access, require_roles
from .clock import now, timestamp
from .db import get_db
from .support import (
    RETENTION,
    _conflict,
    _envelope,
    _invalid,
    _not_found,
    _payload,
    _text,
    _transaction,
    _uuid,
    record_state_event,
    request_details,
)

bp = Blueprint("agent_support", __name__, url_prefix="/v1/agent/escalations")
STATES = ("queued", "assigned", "in_review", "waiting_for_customer", "resolved")
TRANSITIONS = {
    "assigned": ("in_review", "queued"),
    "in_review": ("waiting_for_customer", "resolved", "queued"),
    "waiting_for_customer": ("in_review", "queued"),
}


def _retained(connection, request_id):
    row = connection.execute(
        "SELECT * FROM support_requests WHERE request_id=? AND (resolved_at IS NULL OR resolved_at>?)",
        (request_id, now() - RETENTION),
    ).fetchone()
    if row is None:
        _not_found()
    return row


def _summary(row):
    return dict(
        request_id=row["request_id"],
        state=row["state"],
        content=row["content"],
        reason=row["reason"],
        created_at=timestamp(row["created_at"]),
        assigned_agent_id=row["assigned_agent_id"],
        customer_ref=row["customer_id"],
        account_status=None,
        version=row["version"],
    )


def _cursor_codec():
    return URLSafeSerializer(current_app.secret_key, salt="agent-queue-v1")


def _read_cursor(value, agent, state):
    try:
        if len(value) > 2048:
            raise ValueError
        data = _cursor_codec().loads(value)
        if (
            not isinstance(data, dict)
            or data.get("agent") != agent
            or data.get("state") != state
        ):
            raise ValueError
        if (
            type(data.get("expires_at")) is not int
            or data["expires_at"] <= now()
            or type(data.get("created_at")) is not int
        ):
            raise ValueError
        if not isinstance(data.get("request_id"), str) or len(data["request_id"]) > 200:
            raise ValueError
        return data["created_at"], data["request_id"]
    except (BadSignature, ValueError, TypeError):
        _invalid("This queue cursor is invalid or expired. Reload the queue.")


@bp.get("")
@require_roles("agent")
def list_requests():
    if request.args.keys() - {"state", "limit", "cursor"} or any(
        len(request.args.getlist(k)) != 1 for k in request.args
    ):
        _invalid("Use only one state, limit and cursor.")
    state = request.args.get("state")
    if state is not None and state not in STATES:
        _invalid("Choose a supported request state.")
    raw_limit = request.args.get("limit", "25")
    if (
        not raw_limit.isascii()
        or not raw_limit.isdecimal()
        or len(raw_limit) > 3
        or not 1 <= int(raw_limit) <= 100
    ):
        _invalid("Use a queue limit between 1 and 100.")
    limit = int(raw_limit)
    agent = current_access().subject_id
    cursor = request.args.get("cursor")
    position = _read_cursor(cursor, agent, state) if cursor else None
    where = "(assigned_agent_id=? OR (state='queued' AND assigned_agent_id IS NULL)) AND (resolved_at IS NULL OR resolved_at>?)"
    values = [agent, now() - RETENTION]
    if state:
        where += " AND state=?"
        values.append(state)
    if position:
        where += " AND (created_at,request_id)>(?,?)"
        values.extend(position)
    rows = (
        get_db()
        .execute(
            f"SELECT * FROM support_requests WHERE {where} ORDER BY created_at,request_id LIMIT ?",
            (*values, limit + 1),
        )
        .fetchall()
    )
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _cursor_codec().dumps(
            dict(
                agent=agent,
                state=state,
                created_at=last["created_at"],
                request_id=last["request_id"],
                expires_at=now() + 900,
            )
        )
    return _envelope(
        items=[_summary(row) for row in rows[:limit]], next_cursor=next_cursor
    )


@bp.get("/<request_id>")
@require_roles("agent")
def details(request_id):
    _uuid(request_id, "request_id")
    connection = get_db()
    try:
        connection.execute("BEGIN")
        row = _retained(connection, request_id)
        if row["assigned_agent_id"] != current_access().subject_id:
            _not_found()
        result = {**_summary(row), **request_details(connection, row, agent=True)}
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return _envelope(**result)


@bp.post("/<request_id>/claim")
@require_roles("agent")
def claim(request_id):
    _uuid(request_id, "request_id")
    if request.get_data():
        _invalid("Claim does not accept a request body.")
    agent = current_access().subject_id
    with _transaction(agent_update=True) as connection:
        row = _retained(connection, request_id)
        if row["state"] != "queued" or row["assigned_agent_id"] is not None:
            _conflict("This request has already been claimed. Reload the queue.")
        changed = connection.execute(
            "UPDATE support_requests SET state='assigned',assigned_agent_id=?,version=version+1 WHERE request_id=? AND state='queued' AND assigned_agent_id IS NULL AND version=?",
            (agent, request_id, row["version"]),
        ).rowcount
        if changed != 1:
            _conflict()
        record_state_event(connection, row, "assigned", "claim")
        result = _summary(_retained(connection, request_id))
    return _envelope(**result)


@bp.post("/<request_id>/transition")
@require_roles("agent")
def transition(request_id):
    _uuid(request_id, "request_id")
    body = _payload(
        ("to_state", "expected_version"),
        ("message_to_customer", "resolution_note", "release_reason"),
    )
    target, version = body["to_state"], body["expected_version"]
    if (
        target not in STATES
        or type(version) is not int
        or not 1 <= version <= 2147483647
    ):
        _invalid("Provide a supported to_state and positive expected_version.")
    field = {
        "waiting_for_customer": "message_to_customer",
        "resolved": "resolution_note",
        "queued": "release_reason",
    }.get(target)
    if body.keys() - {"to_state", "expected_version"} - ({field} if field else set()):
        _invalid("Include only the text required for this transition.")
    text = (
        _text(body.get(field), field, 500 if target == "queued" else 2000)
        if field
        else None
    )
    agent = current_access().subject_id
    with _transaction(agent_update=True) as connection:
        row = _retained(connection, request_id)
        if (
            row["assigned_agent_id"] != agent
            or row["version"] != version
            or target not in TRANSITIONS.get(row["state"], ())
        ):
            _conflict()
        changed = connection.execute(
            "UPDATE support_requests SET state=?,assigned_agent_id=?,version=version+1,resolved_at=? WHERE request_id=? AND assigned_agent_id=? AND version=? AND state=?",
            (
                target,
                None if target == "queued" else agent,
                now() if target == "resolved" else None,
                request_id,
                agent,
                version,
                row["state"],
            ),
        ).rowcount
        if changed != 1:
            _conflict()
        if field and target != "queued":
            connection.execute(
                "INSERT INTO support_agent_messages (message_id,request_id,agent_id,kind,content,created_at,request_version) VALUES (?,?,?,?,?,?,?)",
                (str(uuid4()), request_id, agent, field, text, now(), version + 1),
            )
        record_state_event(
            connection, row, target, "transition", reason_given=target == "queued"
        )
        result = _summary(_retained(connection, request_id))
    return _envelope(**result)


def init_app(app):
    app.register_blueprint(bp)
