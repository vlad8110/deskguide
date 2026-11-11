"""Customer reply contracts checked against real routes and browser operations."""

import json
import shutil
import subprocess
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

from app.db import get_db


@pytest.fixture
def reply_contract(app, client, sign_in):
    sign_in(client)
    headers = {"X-CSRF-Token": client.get("/v1/session").json["csrf_token"]}

    def post(path, body):
        return client.post(path, json=body, headers=headers)

    sid = post("/v1/escalations/submission-ids", {"operation": "escalation"}).json[
        "submission_id"
    ]
    saved = post(
        "/v1/escalations",
        {
            "submission_id": sid,
            "reason": "human_requested",
            "content": "Fictional VPN support request",
            "consent_to_share": True,
        },
    )
    assert saved.status_code == 201
    rid = saved.json["request_id"]
    with app.app_context(), get_db() as db:
        db.execute(
            "UPDATE support_requests SET state='waiting_for_customer', "
            "assigned_agent_id='a1', version=4 WHERE request_id=?",
            (rid,),
        )
    return rid, sid, post


def test_reply_contract_response_fields(client, reply_contract):
    rid, original_sid, post = reply_contract
    registration = post(f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"})
    assert registration.status_code == 201
    for response in (
        registration,
        client.get(f"/v1/escalations/{registration.json['submission_id']}"),
        client.get(f"/v1/escalations/{original_sid}"),
        client.get(f"/v1/escalations/requests/{rid}"),
    ):
        data = response.json
        assert data["contract_version"] == "0.3.3"
        assert data["request_id"] == rid
        assert type(data["version"]) is int and data["version"] == 4
        assert data["state"] == "waiting_for_customer"
    assert registration.json["operation"] == "reply"
    assert registration.json["registration_state"] == "unused"


def test_reply_contract_distinct_conflicts(app, client, reply_contract):
    rid, _, post = reply_contract
    sid = post(f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}).json[
        "submission_id"
    ]
    second_sid = post(f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"}).json[
        "submission_id"
    ]
    path = f"/v1/escalations/{rid}/replies"
    body = {"submission_id": sid, "message": "Reviewed reply", "expected_version": 3}
    stale = post(path, body)
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "STALE_VERSION"
    body["expected_version"] = 4
    assert post(path, body).status_code == 201
    changed = post(path, {**body, "message": "Different content"})
    assert changed.status_code == 409
    assert changed.json["error"]["code"] == "CONFLICT"
    assert post(path, body).status_code == 200  # Same payload replays, not duplicates.
    no_longer_waiting = post(path, {**body, "submission_id": second_sid})
    assert no_longer_waiting.status_code == 409
    assert no_longer_waiting.json["error"]["code"] == "NOT_WAITING_FOR_CUSTOMER"
    closed = post(f"/v1/escalations/{rid}/reply-ids", {"operation": "reply"})
    assert closed.status_code == 409
    assert closed.json["error"]["code"] == "NOT_WAITING_FOR_CUSTOMER"
    with app.app_context():
        assert (
            get_db().execute("SELECT COUNT(*) FROM support_replies").fetchone()[0] == 1
        )
    assert client.get(f"/v1/escalations/requests/{rid}").json["version"] == 5


@pytest.mark.parametrize("omit", ["none", "detail", "registration"])
def test_reply_browser_against_real_backend(app, reply_contract, omit):
    node = shutil.which("node")
    assert node, "Node is required for browser/backend contract checks (also in CI)."
    rid, _, _ = reply_contract
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [node, str(Path(__file__).parent / "contracts/customer-reply.cjs")],
            input=json.dumps(
                {
                    "base": f"http://127.0.0.1:{server.server_port}",
                    "requestId": rid,
                    "omit": omit,
                }
            ),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    with app.app_context():
        replies = get_db().execute("SELECT content FROM support_replies").fetchall()
        assert len(replies) == (1 if omit == "none" else 0)
