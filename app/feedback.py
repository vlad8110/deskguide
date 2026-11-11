"""C6a customer feedback for retained inquiries."""

import unicodedata
from uuid import UUID, uuid4

import click
from flask import Blueprint, g, jsonify, request
from flask.cli import with_appcontext

from .access import current_access, require_roles
from .clock import now
from .db import get_db
from .errors import CONTRACT_VERSION, ApiError

bp = Blueprint("feedback", __name__, url_prefix="/v1/feedback")
COMMON_CATEGORIES = ("unclear", "other")
ANSWERED_CATEGORIES = (*COMMON_CATEGORIES, "incorrect", "incomplete", "wrong_source")
UNANSWERED_CATEGORIES = (
    *COMMON_CATEGORIES,
    "too_much_escalation",
    "fallback_unhelpful",
)


def _validate_payload(payload):
    required = {"inquiry_id", "rating"}
    if (
        not isinstance(payload, dict)
        or not required <= payload.keys()
        or payload.keys() - required - {"category", "comment"}
    ):
        raise ApiError(400, "VALIDATION_FAILED", "Provide the feedback fields only.")

    inquiry_id = payload["inquiry_id"]
    try:
        if not isinstance(inquiry_id, str) or str(UUID(inquiry_id)) != inquiry_id:
            raise ValueError
    except ValueError:
        raise ApiError(
            400, "VALIDATION_FAILED", "Provide a valid inquiry_id."
        ) from None

    rating = payload["rating"]
    category = payload.get("category")
    if rating not in ("helpful", "not_helpful"):
        raise ApiError(400, "VALIDATION_FAILED", "Choose a supported rating.")
    if category is not None and rating != "not_helpful":
        raise ApiError(400, "VALIDATION_FAILED", "A category requires not_helpful.")

    comment = payload.get("comment")
    if comment is not None:
        if not isinstance(comment, str) or any(
            unicodedata.category(character) in {"Cc", "Cs"}
            and character not in "\n\r\t"
            for character in comment
        ):
            raise ApiError(400, "VALIDATION_FAILED", "Provide a plain-text comment.")
        comment = unicodedata.normalize("NFC", comment).strip() or None
        if comment is not None and len(comment) > 500:
            raise ApiError(400, "VALIDATION_FAILED", "Use 500 characters or fewer.")
    return inquiry_id, rating, category, comment


@bp.post("")
@require_roles("customer")
def submit():
    inquiry_id, rating, category, comment = _validate_payload(
        request.get_json(silent=True)
    )
    customer_id = current_access().customer_scope
    feedback_id = str(uuid4())
    with get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        created_at = now()
        inquiry = connection.execute(
            "SELECT outcome FROM inquiries WHERE inquiry_id=? AND customer_id=? "
            "AND expires_at>? AND outcome != 'processing'",
            (inquiry_id, customer_id, created_at),
        ).fetchone()
        if inquiry is None:
            raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")

        categories = (
            ANSWERED_CATEGORIES
            if inquiry["outcome"] == "answered"
            else UNANSWERED_CATEGORIES
        )
        if category is not None and category not in categories:
            raise ApiError(
                400, "VALIDATION_FAILED", "Choose a category for this inquiry outcome."
            )
        if connection.execute(
            "SELECT 1 FROM feedback WHERE inquiry_id=? AND customer_id=? AND rating IS NOT NULL",
            (inquiry_id, customer_id),
        ).fetchone():
            raise ApiError(409, "CONFLICT", "Feedback for this inquiry already exists.")

        # The inquiry FK retains the trusted outcome, route, configuration and answer link.
        connection.execute(
            "INSERT INTO feedback "
            "(feedback_id, inquiry_id, customer_id, rating, category, comment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                feedback_id,
                inquiry_id,
                customer_id,
                rating,
                category,
                comment,
                created_at,
            ),
        )
    return jsonify(
        contract_version=CONTRACT_VERSION,
        correlation_id=g.correlation_id,
        feedback_id=feedback_id,
        state="pending_review",
    ), 201


@click.command("cleanup-inquiries")
@with_appcontext
def cleanup_inquiries_command():
    """Remove expired inquiry metadata and its linked feedback."""
    with get_db() as connection:
        removed = connection.execute(
            "DELETE FROM inquiries WHERE expires_at<=?", (now(),)
        ).rowcount
    click.echo(f"Removed {removed} expired inquiries and their linked feedback.")


def init_app(app):
    app.register_blueprint(bp)
    app.cli.add_command(cleanup_inquiries_command)
