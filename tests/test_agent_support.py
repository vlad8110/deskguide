"""C5 queue visibility, versioned ownership, state races and audit regressions."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from app import support
from app.db import get_db

BASE = "/v1/agent/escalations"
OMITTED = object()


def post(api, path, body=OMITTED):
    options = {"headers": api[1]}
    if body is not OMITTED:
        options["json"] = body
    return api[0].post(path, **options)


def transition(api, rid, target, version, **fields):
    return post(
        api,
        f"{BASE}/{rid}/transition",
        dict(to_state=target, expected_version=version, **fields),
    )


@pytest.fixture
def api_factory(app, sign_in):
    cached = {}

    def make(username):
        if username not in cached:
            client = app.test_client()
            assert sign_in(client, username).status_code == 200
            cached[username] = (
                client,
                {"X-CSRF-Token": client.get("/v1/session").json["csrf_token"]},
            )
        return cached[username]

    return make


@pytest.fixture
def new_request(api_factory):
    def make(username="customer-one", text="Fictional support request"):
        api = api_factory(username)
        sid = post(
            api, "/v1/escalations/submission-ids", {"operation": "escalation"}
        ).json["submission_id"]
        response = post(
            api,
            "/v1/escalations",
            dict(
                submission_id=sid,
                content=text,
                note="Private reviewed note",
                reason="human_requested",
                consent_to_share=True,
            ),
        )
        assert response.status_code == 201
        return response.json["request_id"]

    return make


@pytest.fixture
def owned(new_request, api_factory):
    rid = new_request()
    agent = api_factory("agent-one")
    assert post(agent, f"{BASE}/{rid}/claim").status_code == 200
    return rid, agent


@pytest.fixture
def waiting(owned):
    rid, agent = owned
    assert transition(agent, rid, "in_review", 2).status_code == 200
    assert (
        transition(
            agent,
            rid,
            "waiting_for_customer",
            3,
            message_to_customer="Which fictional network are you using?",
        ).status_code
        == 200
    )
    return rid, agent


def test_queue_contains_only_unassigned_and_own_requests(api_factory, new_request):
    a1, a2 = api_factory("agent-one"), api_factory("agent-two")
    own, foreign, queued = new_request(), new_request("customer-two"), new_request()
    assert post(a1, f"{BASE}/{own}/claim").status_code == 200
    assert post(a2, f"{BASE}/{foreign}/claim").status_code == 200
    result = a1[0].get(BASE).json
    assert {r["request_id"] for r in result["items"]} == {own, queued}
    for row in result["items"]:
        assert row["account_status"] is None
        assert set(row) == {
            "request_id",
            "state",
            "content",
            "reason",
            "created_at",
            "assigned_agent_id",
            "customer_ref",
            "account_status",
            "version",
        }
        assert "Private reviewed note" not in str(row)
    assert [
        r["request_id"] for r in a1[0].get(BASE + "?state=queued").json["items"]
    ] == [queued]
    assert a1[0].get(f"{BASE}/{foreign}").status_code == 404
    assert a1[0].get(f"{BASE}/{queued}").status_code == 404
    assert a1[0].get(f"{BASE}/{own}").json["note"] == "Private reviewed note"


def test_queue_keyset_pagination_is_bounded_scoped_and_signed(api_factory, new_request):
    agent = api_factory("agent-one")
    expected = {new_request() for _ in range(3)}
    first = agent[0].get(BASE + "?state=queued&limit=2").json
    assert len(first["items"]) == 2 and first["next_cursor"]
    cursor = first["next_cursor"]
    second = (
        agent[0]
        .get(BASE, query_string=dict(state="queued", limit=2, cursor=cursor))
        .json
    )
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    assert {r["request_id"] for r in first["items"] + second["items"]} == expected
    for query in [
        dict(state="queued", cursor=cursor + "tampered"),
        dict(state="assigned", cursor=cursor),
    ]:
        assert agent[0].get(BASE, query_string=query).status_code == 400
    other = api_factory("agent-two")
    assert (
        other[0].get(BASE, query_string=dict(state="queued", cursor=cursor)).status_code
        == 400
    )


def test_queue_cursor_expires_without_expiring_agent_session(
    api_factory, new_request, clock
):
    new_request()
    new_request()
    agent = api_factory("agent-one")
    cursor = agent[0].get(BASE + "?limit=1").json["next_cursor"]
    clock[0] += 900
    assert agent[0].get(BASE, query_string={"cursor": cursor}).status_code == 400


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=-1",
        "limit=true",
        "limit=1&limit=2",
        "state=bad",
        "state=queued&state=assigned",
        "agent_id=a2",
        "customer_id=c2",
        "cursor=bad",
    ],
)
def test_invalid_queue_queries_do_not_widen_scope(api_factory, query):
    agent = api_factory("agent-one")
    assert agent[0].get(BASE + "?" + query).status_code == 400


@pytest.mark.parametrize("username", ["customer-one", "admin-one"])
def test_nonagents_cannot_use_any_c5_route(api_factory, new_request, username):
    rid = new_request()
    api = api_factory(username)
    assert api[0].get(BASE).status_code == 403
    assert api[0].get(f"{BASE}/{rid}").status_code == 403
    assert post(api, f"{BASE}/{rid}/claim").status_code == 403
    assert transition(api, rid, "in_review", 1).status_code == 403


def test_anonymous_and_missing_csrf_actions_are_denied(app, api_factory, new_request):
    rid = new_request()
    client = app.test_client()
    assert client.get(BASE).status_code == 401
    assert client.post(f"{BASE}/{rid}/claim").status_code == 401
    agent = api_factory("agent-one")
    assert agent[0].post(f"{BASE}/{rid}/claim").json["error"]["code"] == "CSRF_FAILED"
    assert (
        agent[0].post(f"{BASE}/{rid}/transition", json={}).json["error"]["code"]
        == "CSRF_FAILED"
    )


def test_claim_has_no_body_and_uses_server_identity(api_factory, new_request):
    rid = new_request()
    agent = api_factory("agent-one")
    assert (
        post(agent, f"{BASE}/{rid}/claim", {"assigned_agent_id": "a2"}).status_code
        == 400
    )
    response = post(agent, f"{BASE}/{rid}/claim")
    assert response.status_code == 200
    assert response.json["state"] == "assigned" and response.json["version"] == 2
    assert response.json["assigned_agent_id"] == "a1"
    assert post(agent, f"{BASE}/{rid}/claim").status_code == 409


def test_nonowner_update_conflicts_without_changing_or_exposing_content(
    owned, api_factory
):
    rid, _ = owned
    other = api_factory("agent-two")
    response = transition(other, rid, "in_review", 2)
    assert (
        response.status_code == 409 and "Fictional support request" not in response.text
    )
    assert other[0].get(f"{BASE}/{rid}").status_code == 404
    assert transition(other, str(uuid4()), "in_review", 2).status_code == 404


def test_full_agent_customer_lifecycle_preserves_owner_and_content_free_audit(
    app, waiting, api_factory
):
    rid, agent = waiting
    customer = api_factory("customer-one")
    detail = customer[0].get(f"/v1/escalations/requests/{rid}").json
    assert (
        detail["version"] == 4
        and detail["messages"][0]["kind"] == "message_to_customer"
    )
    sid = post(
        customer, f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}
    ).json["submission_id"]
    reply = post(
        customer,
        f"/v1/escalations/{rid}/replies",
        dict(
            submission_id=sid,
            message="I am on the fictional Campus network.",
            expected_version=4,
        ),
    )
    assert reply.status_code == 201 and reply.json["state"] == "in_review"
    assert (
        transition(
            agent, rid, "resolved", 5, resolution_note="Internal resolution note"
        ).status_code
        == 200
    )
    detail = agent[0].get(f"{BASE}/{rid}").json
    assert detail["assigned_agent_id"] == "a1" and detail["version"] == 6
    assert [m["version"] for m in detail["messages"]] == [4, 5, 6]
    public = customer[0].get(f"/v1/escalations/requests/{rid}").json
    assert [m["kind"] for m in public["messages"]] == [
        "message_to_customer",
        "customer_reply",
    ]
    assert "Internal resolution note" not in str(public)
    assert (
        api_factory("customer-two")[0]
        .get(f"/v1/escalations/requests/{rid}")
        .status_code
        == 404
    )
    assert (
        api_factory("admin-one")[0].get(f"/v1/escalations/requests/{rid}").status_code
        == 403
    )
    with app.app_context():
        events = (
            get_db()
            .execute(
                "SELECT * FROM support_state_events WHERE request_id=? ORDER BY version",
                (rid,),
            )
            .fetchall()
        )
        assert [(r["from_state"], r["to_state"], r["version"]) for r in events] == [
            ("queued", "assigned", 2),
            ("assigned", "in_review", 3),
            ("in_review", "waiting_for_customer", 4),
            ("waiting_for_customer", "in_review", 5),
            ("in_review", "resolved", 6),
        ]
        assert events[3]["actor_role"] == "customer"
        assert "network" not in str([dict(r) for r in events])


@pytest.mark.parametrize("initial", ["assigned", "in_review", "waiting_for_customer"])
def test_release_requires_reason_clears_ownership_and_allows_new_claim(
    app, owned, api_factory, initial
):
    rid, agent = owned
    version = 2
    if initial != "assigned":
        transition(agent, rid, "in_review", version)
        version += 1
    if initial == "waiting_for_customer":
        transition(
            agent, rid, initial, version, message_to_customer="Question for customer"
        )
        version += 1
    assert transition(agent, rid, "queued", version).status_code == 400
    response = transition(
        agent,
        rid,
        "queued",
        version,
        release_reason="Private release reason not retained",
    )
    assert response.status_code == 200 and response.json["assigned_agent_id"] is None
    assert agent[0].get(f"{BASE}/{rid}").status_code == 404
    second = api_factory("agent-two")
    assert post(second, f"{BASE}/{rid}/claim").json["assigned_agent_id"] == "a2"
    assert (
        transition(agent, rid, "in_review", response.json["version"]).status_code == 409
    )
    with app.app_context():
        event = (
            get_db()
            .execute("SELECT * FROM support_state_events WHERE to_state='queued'")
            .fetchone()
        )
        assert event["reason_given"] == 1 and event["actor_id"] == "a1"
        for table in (
            "support_requests",
            "support_state_events",
            "support_agent_messages",
        ):
            assert "Private release reason" not in str(
                [dict(r) for r in get_db().execute(f"SELECT * FROM {table}")]
            )


@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {"to_state": []},
        {"to_state": "bad", "expected_version": 2},
        {"to_state": "in_review", "expected_version": True},
        {"to_state": "in_review", "expected_version": 0},
        {"to_state": "in_review", "expected_version": "2"},
        {"to_state": "in_review", "expected_version": 2, "assigned_agent_id": "a2"},
        {
            "to_state": "in_review",
            "expected_version": 2,
            "resolution_note": "Unrelated",
        },
    ],
)
def test_invalid_transition_payload_does_not_mutate(app, owned, body):
    rid, agent = owned
    assert post(agent, f"{BASE}/{rid}/transition", body).status_code == 400
    assert agent[0].get(f"{BASE}/{rid}").json["version"] == 2


@pytest.mark.parametrize(
    "target,fields",
    [
        ("waiting_for_customer", {}),
        ("waiting_for_customer", {"message_to_customer": ""}),
        ("waiting_for_customer", {"message_to_customer": "x" * 2001}),
        ("resolved", {}),
        ("resolved", {"resolution_note": ""}),
        ("queued", {"release_reason": "x" * 501}),
    ],
)
def test_conditional_transition_text_is_validated(owned, target, fields):
    rid, agent = owned
    assert transition(agent, rid, "in_review", 2).status_code == 200
    assert transition(agent, rid, target, 3, **fields).status_code == 400
    assert agent[0].get(f"{BASE}/{rid}").json["version"] == 3


def test_forbidden_state_shortcuts_and_stale_updates_do_not_overwrite(owned):
    rid, agent = owned
    assert (
        transition(agent, rid, "resolved", 2, resolution_note="Shortcut").status_code
        == 409
    )
    assert (
        transition(
            agent, rid, "waiting_for_customer", 2, message_to_customer="Shortcut"
        ).status_code
        == 409
    )
    assert transition(agent, rid, "in_review", 1).status_code == 409
    assert transition(agent, rid, "assigned", 2).status_code == 409
    assert transition(agent, rid, "in_review", 2).status_code == 200
    assert (
        transition(agent, rid, "resolved", 3, resolution_note="Done").status_code == 200
    )
    for target, extra in [
        ("in_review", {}),
        ("queued", {"release_reason": "Cannot reopen"}),
        ("waiting_for_customer", {"message_to_customer": "Cannot reopen"}),
    ]:
        assert transition(agent, rid, target, 4, **extra).status_code == 409


def test_two_simultaneous_agents_claim_once(app, new_request, api_factory):
    rid = new_request()
    agents = [api_factory("agent-one"), api_factory("agent-two")]
    barrier = Barrier(2)

    def work(agent):
        barrier.wait(timeout=10)
        response = post(agent, f"{BASE}/{rid}/claim")
        return response.status_code, response.json.get("assigned_agent_id")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(work, agents))
    assert sorted(r[0] for r in results) == [200, 409]
    winner = next(r[1] for r in results if r[0] == 200)
    with app.app_context():
        assert tuple(
            get_db()
            .execute(
                "SELECT assigned_agent_id,version FROM support_requests WHERE request_id=?",
                (rid,),
            )
            .fetchone()
        ) == (winner, 2)
        assert (
            get_db().execute("SELECT COUNT(*) FROM support_state_events").fetchone()[0]
            == 1
        )


def clone_client(app, api):
    client = app.test_client()
    client.set_cookie("deskguide_session", api[0].get_cookie("deskguide_session").value)
    return client, api[1]


def test_simultaneous_owner_updates_apply_once(app, owned):
    rid, agent = owned
    apis = [clone_client(app, agent), clone_client(app, agent)]
    barrier = Barrier(2)

    def work(api):
        barrier.wait(timeout=10)
        return transition(api, rid, "in_review", 2).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(work, apis))
    assert sorted(results) == [200, 409]
    assert agent[0].get(f"{BASE}/{rid}").json["version"] == 3


def test_actual_resolution_endpoint_races_customer_reply_without_reopening(
    app, waiting, api_factory
):
    rid, agent = waiting
    customer = api_factory("customer-one")
    sid = post(
        customer, f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}
    ).json["submission_id"]
    # The owner returns to review while the customer's already-issued reply remains unused.
    assert transition(agent, rid, "in_review", 4).status_code == 200
    barrier = Barrier(2)

    def resolve():
        barrier.wait(timeout=10)
        return transition(
            agent, rid, "resolved", 5, resolution_note="Resolved after review"
        ).status_code

    def reply():
        barrier.wait(timeout=10)
        return post(
            customer,
            f"/v1/escalations/{rid}/replies",
            dict(submission_id=sid, message="Late reply", expected_version=4),
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(resolve), pool.submit(reply)
        assert a.result(timeout=15) == 200 and b.result(timeout=15) == 409
    assert agent[0].get(f"{BASE}/{rid}").json["state"] == "resolved"


def test_customer_reply_races_owner_review_with_one_version_winner(
    app, waiting, api_factory
):
    rid, agent = waiting
    customer = api_factory("customer-one")
    sid = post(
        customer, f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}
    ).json["submission_id"]
    barrier = Barrier(2)
    reply_body = dict(
        submission_id=sid, message="Customer response", expected_version=4
    )

    def owner_review():
        barrier.wait(timeout=10)
        return transition(agent, rid, "in_review", 4).status_code

    def customer_reply():
        barrier.wait(timeout=10)
        return post(customer, f"/v1/escalations/{rid}/replies", reply_body).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(owner_review), pool.submit(customer_reply)
        owner_status, reply_status = a.result(timeout=15), b.result(timeout=15)
    assert (owner_status, reply_status) in ((200, 409), (409, 201))
    assert agent[0].get(f"{BASE}/{rid}").json["version"] == 5
    assert (
        transition(
            agent, rid, "resolved", 5, resolution_note="Completed review"
        ).status_code
        == 200
    )
    retry = post(customer, f"/v1/escalations/{rid}/replies", reply_body)
    assert retry.status_code == (200 if reply_status == 201 else 409)
    assert agent[0].get(f"{BASE}/{rid}").json["state"] == "resolved"


class BrokenWrite:
    def __init__(self, connection, *, commit=False):
        self.connection, self.break_commit = connection, commit

    def execute(self, sql, *args):
        if not self.break_commit and sql.startswith("INSERT INTO support_state_events"):
            raise sqlite3.OperationalError("Private transition text must not be logged")
        return self.connection.execute(sql, *args)

    def commit(self):
        self.connection.commit()
        if self.break_commit:
            raise TimeoutError("Commit acknowledgement lost")

    def rollback(self):
        self.connection.rollback()


@pytest.mark.parametrize("commit", [False, True])
def test_audit_failure_rolls_back_and_unknown_commit_requires_reload(
    app, new_request, api_factory, monkeypatch, caplog, commit
):
    rid = new_request()
    agent = api_factory("agent-one")
    original = support.get_db
    with monkeypatch.context() as patch:
        patch.setattr(support, "get_db", lambda: BrokenWrite(original(), commit=commit))
        response = post(agent, f"{BASE}/{rid}/claim")
    assert response.status_code == 503
    assert response.json["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "Private transition text" not in response.text + caplog.text
    if commit:
        assert "Reload" in response.json["error"]["message"]
        assert agent[0].get(f"{BASE}/{rid}").json["version"] == 2
        assert post(agent, f"{BASE}/{rid}/claim").status_code == 409
    else:
        assert agent[0].get(f"{BASE}/{rid}").status_code == 404
        assert post(agent, f"{BASE}/{rid}/claim").status_code == 200


def test_retention_hides_all_views_and_cleanup_cascades_messages_and_audit(
    app, waiting, api_factory, clock
):
    rid, agent = waiting
    assert transition(agent, rid, "in_review", 4).status_code == 200
    assert (
        transition(agent, rid, "resolved", 5, resolution_note="Done").status_code == 200
    )
    with app.app_context():
        with get_db() as connection:
            connection.execute(
                "UPDATE support_requests SET resolved_at=? WHERE request_id=?",
                (clock[0] - support.RETENTION, rid),
            )
    assert agent[0].get(f"{BASE}/{rid}").status_code == 404
    assert agent[0].get(BASE).json["items"] == []
    customer = api_factory("customer-one")
    assert customer[0].get(f"/v1/escalations/requests/{rid}").status_code == 404
    result = app.test_cli_runner().invoke(args=["cleanup-support"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        for table in (
            "support_requests",
            "support_state_events",
            "support_agent_messages",
        ):
            assert get_db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
