"""Role, permission and customer/agent ownership regressions."""

import pytest
from flask import g

from app.access import (
    AccessContext,
    check_independent_authorizer,
    check_permission,
    require_permission,
)
from app.accounts import change_access
from app.errors import ApiError


@pytest.mark.parametrize(
    "username,status", [("customer-one", 403), ("agent-one", 403), ("admin-one", 200)]
)
def test_document_administration_is_separate(client, sign_in, username, status):
    sign_in(client, username)
    assert client.get("/test/admin").status_code == status


def test_missing_login_denies_role_guard(client):
    assert client.get("/test/admin").status_code == 401


@pytest.mark.parametrize(
    "username,request_id,status",
    [
        ("customer-one", "r1", 200),
        ("customer-one", "r2", 404),
        ("customer-two", "r1", 404),
        ("agent-one", "r1", 200),
        ("agent-one", "r2", 404),
        ("agent-two", "r1", 404),
        ("admin-one", "r1", 403),
        ("customer-one", "absent", 404),
    ],
)
def test_request_content_is_scoped(
    client, sign_in, support_records, username, request_id, status
):
    sign_in(client, username)
    response = client.get("/test/support/" + request_id)
    assert response.status_code == status
    if status != 200:
        assert "Private fictional" not in response.text


def test_client_supplied_scope_cannot_change_access(client, sign_in, support_records):
    sign_in(client)
    response = client.get(
        "/test/support/r2?customer_id=c2&role=agent",
        headers={"X-User-ID": "u2", "X-Role": "administrator"},
    )
    assert response.status_code == 404


def test_review_permission_is_not_implied_by_staff_role(app):
    with app.test_request_context():
        g.access = AccessContext("a1", "agent", None, frozenset(), "test")
        with pytest.raises(ApiError) as error:
            check_permission("reviewer")
        assert error.value.status == 403


def test_author_cannot_authorize_own_release(app):
    with app.test_request_context():
        g.access = AccessContext(
            "a1", "agent", None, frozenset({"release_authorizer"}), "test"
        )
        with pytest.raises(ApiError) as error:
            check_independent_authorizer("a1")
        assert error.value.status == 403
        assert error.value.code == "FORBIDDEN"
        assert check_independent_authorizer("a2").subject_id == "a1"


def test_customer_cannot_gain_staff_permission(app):
    with app.test_request_context():
        g.access = AccessContext(
            "u1", "customer", "c1", frozenset({"reviewer"}), "test"
        )
        with pytest.raises(ApiError):
            check_permission("reviewer")


@pytest.mark.parametrize(
    "username,permission,status",
    [
        (None, False, 401),
        ("customer-one", False, 403),
        ("agent-one", False, 403),
        ("agent-one", True, 200),
    ],
)
def test_permission_decorator_uses_live_authorization(
    app, client, sign_in, username, permission, status
):
    @app.get("/test/reviewer")
    @require_permission("reviewer")
    def review():
        return {"ok": True}

    if permission:
        with app.app_context():
            change_access("a1", "agent", None, ["reviewer"])
    if username:
        assert sign_in(client, username).status_code == 200
    assert client.get("/test/reviewer").status_code == status
