"""Isolated application data, clocks, clients and authorization probes."""

import pytest
from flask import jsonify
from werkzeug.security import generate_password_hash

from app import create_app
from app.access import current_access, get_owned_support_request, require_roles
from app.db import get_db, init_db

PASSWORD = "Test-only-passphrase-12!"
PASSWORD_HASH = generate_password_hash(PASSWORD)


@pytest.fixture
def clock():
    return [2_000_000_000]


@pytest.fixture
def app(tmp_path, clock):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "deskguide.sqlite3"),
            "SESSION_COOKIE_SECURE": False,
            # Cleanup has its own deterministic test; avoid random writes here.
            "SESSION_CLEANUP_N_REQUESTS": None,
            "TIME_PROVIDER": lambda: clock[0],
            "DUMMY_PASSWORD_HASH": PASSWORD_HASH,
        }
    )
    with app.app_context():
        init_db()
        with get_db() as db:
            db.executemany(
                "INSERT INTO customers (customer_id, display_name) VALUES (?, ?)",
                [("c1", "Fictional One"), ("c2", "Fictional Two")],
            )
            db.executemany(
                "INSERT INTO users (user_id, username, password_hash, role, customer_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (uid, name, PASSWORD_HASH, role, customer, clock[0])
                    for uid, name, role, customer in [
                        ("u1", "customer-one", "customer", "c1"),
                        ("u2", "customer-two", "customer", "c2"),
                        ("a1", "agent-one", "agent", None),
                        ("a2", "agent-two", "agent", None),
                        ("d1", "admin-one", "administrator", None),
                    ]
                ],
            )

    # Test routes exercise the reusable access layer without claiming C4-C8 endpoints exist.
    @app.get("/test/admin")
    @require_roles("administrator")
    def admin_probe():
        return jsonify(ok=True)

    @app.post("/test/write")
    @require_roles("customer")
    def write_probe():
        return jsonify(ok=True)

    @app.get("/test/support/<request_id>")
    def support_probe(request_id):
        row = get_owned_support_request(current_access(), request_id)
        return jsonify(content=row["content"])

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sign_in():
    def login(client, username="customer-one", password=PASSWORD, **extra):
        token = client.get("/v1/session/login-token").json["csrf_token"]
        return client.post(
            "/v1/session/login",
            json={"username": username, "password": password, **extra},
            headers={"X-CSRF-Token": token},
        )

    return login


@pytest.fixture
def support_records(app, clock):
    with app.app_context():
        with get_db() as db:
            for number, customer, agent in [(1, "c1", "a1"), (2, "c2", "a2")]:
                sid, rid = f"s{number}", f"r{number}"
                db.execute(
                    "INSERT INTO submission_registrations "
                    "(submission_id, customer_id, operation, registered_at, expires_at) "
                    "VALUES (?, ?, 'escalation', ?, ?)",
                    (sid, customer, clock[0], clock[0] + 1800),
                )
                db.execute(
                    "INSERT INTO support_requests "
                    "(request_id, submission_id, customer_id, content, reason, state, "
                    "assigned_agent_id, created_at) VALUES (?, ?, ?, ?, ?, 'assigned', ?, ?)",
                    (
                        rid,
                        sid,
                        customer,
                        f"Private fictional request {number}",
                        "customer_requested",
                        agent,
                        clock[0],
                    ),
                )
