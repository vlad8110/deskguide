"""Server-derived identity, permission and ownership guards."""

from dataclasses import dataclass
from functools import wraps

from flask import g

from .db import get_db
from .errors import ApiError


@dataclass(frozen=True)
class AccessContext:
    subject_id: str
    role: str
    customer_scope: str | None
    permissions: frozenset[str]
    correlation_id: str


def current_access():
    context = getattr(g, "access", None)
    if context is None:
        raise ApiError(401, "UNAUTHENTICATED", "Please sign in.")
    return context


def require_roles(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            context = current_access()
            if context.role not in roles:
                raise ApiError(403, "FORBIDDEN", "This action is not permitted.")
            return view(*args, **kwargs)

        return wrapped

    return decorate


def check_permission(permission):
    """Return the trusted context after a service-level permission check."""
    context = current_access()
    if (
        context.role not in {"agent", "administrator"}
        or permission not in context.permissions
    ):
        raise ApiError(403, "FORBIDDEN", "This action is not permitted.")
    return context


def require_permission(permission):
    """Protect a view with the same decorator convention as require_roles."""

    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            check_permission(permission)
            return view(*args, **kwargs)

        return wrapped

    return decorate


def check_independent_authorizer(author_id):
    context = check_permission("release_authorizer")
    if context.subject_id == author_id:
        raise ApiError(403, "FORBIDDEN", "A different authorizer is required.")
    return context


def get_owned_support_request(context, request_id):
    """Full content is restricted to the customer or assigned agent.

    The future unassigned-queue endpoint must return its own bounded summary.
    A document administrator never inherits access to support content.
    """
    if context.role == "customer" and context.customer_scope:
        row = (
            get_db()
            .execute(
                "SELECT * FROM support_requests WHERE request_id = ? AND customer_id = ?",
                (request_id, context.customer_scope),
            )
            .fetchone()
        )
    elif context.role == "agent":
        row = (
            get_db()
            .execute(
                "SELECT * FROM support_requests WHERE request_id = ? AND assigned_agent_id = ?",
                (request_id, context.subject_id),
            )
            .fetchone()
        )
    else:
        raise ApiError(403, "FORBIDDEN", "This action is not permitted.")
    if row is None:
        raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")
    return row
