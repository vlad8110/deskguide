"""Cohere-backed inquiry services over the fictional three-guide release (no network)."""

import hashlib
import json
from pathlib import Path

import pytest
from conftest import PASSWORD_HASH

from app import create_app
from app.cohere_services import (
    ADAPTER_VERSION,
    COHERE_CHAT_URL,
    CohereError,
    CohereGenerator,
    build_inquiry_services,
)
from app.db import get_db
from app.inquiry_types import GenerationPassage, GenerationRequest, SourceRef

CORPUS = Path(__file__).resolve().parent.parent / "sample_documents" / "corpus_v1"
CASES = json.loads((CORPUS / "evaluation_questions.json").read_text())["cases"]
FAKE_KEY = "test-only-not-a-real-key"


class FakeCohere:
    """Stands in for the Cohere Chat v2 endpoint and records every call."""

    def __init__(self, mode="copy"):
        self.mode = mode
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(
            {"url": url, "headers": headers, "body": body, "timeout": timeout}
        )
        if self.mode == "revoke":
            with get_db() as db:
                db.execute("DELETE FROM document_role_grants WHERE source_id='DOC-003'")
        if self.mode == "error":
            raise CohereError("Cohere returned HTTP 500.")
        document = body["documents"][0]
        text = document["data"]["snippet"]
        if self.mode == "drop_clause" and ", " in text:
            rest = text.split(", ", 1)[1]
            text = rest[0].upper() + rest[1:]
        if self.mode == "paraphrase":
            text = "You should probably " + text[0].lower() + text[1:]
        citations = (
            []
            if self.mode == "no_citations"
            else [
                {
                    "start": 0,
                    "end": len(text),
                    "text": text,
                    "sources": [{"type": "document", "id": document["id"]}],
                }
            ]
        )
        return {
            "id": "fake",
            "finish_reason": "COMPLETE",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
                "citations": citations,
            },
        }


def _write(path, value):
    content = json.dumps(value).encode()
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def release(tmp_path):
    """An approved copy of the draft corpus, for tests only; the shipped manifest stays draft."""
    folder = tmp_path / "release"
    folder.mkdir()
    manifest = json.loads((CORPUS / "evidence_manifest.json").read_text())
    manifest.update(review_status="approved", runtime_enabled=True)
    manifest_hash = _write(folder / "evidence_manifest.json", manifest)
    current = {}
    for name in ("DOC-001.v1.json", "DOC-002.v1.json", "DOC-003.v3.json"):
        guide = json.loads((CORPUS / name).read_text())
        guide["review_status"] = "approved"
        digest = _write(folder / name, guide)
        current[guide["source_id"]] = {
            "version": guide["source_version"],
            "sha256": digest,
        }
    path = folder / "release.json"
    _write(path, {"manifest_sha256": manifest_hash, "current": current})
    return path


@pytest.fixture
def ai_app(app, clock, release, monkeypatch):
    monkeypatch.setenv("DESKGUIDE_CITATION_RELEASE", str(release))
    monkeypatch.setenv("COHERE_API_KEY", FAKE_KEY)
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "import-citation-release",
            str(release),
            "--grant-customer",
            "DOC-001",
            "--grant-customer",
            "DOC-002",
            "--grant-customer",
            "DOC-003",
        ]
    )
    assert result.exit_code == 0, result.output
    fake = FakeCohere()

    def make(mode="copy"):
        fake.mode = mode
        restarted = create_app(
            {
                "TESTING": True,
                "DATABASE": app.config["DATABASE"],
                "SESSION_COOKIE_SECURE": False,
                "SESSION_CLEANUP_N_REQUESTS": None,
                "TIME_PROVIDER": lambda: clock[0],
                "DUMMY_PASSWORD_HASH": PASSWORD_HASH,
            },
            inquiry_services_factory=lambda a: build_inquiry_services(
                a, transport=fake
            ),
        )
        return restarted, fake

    return make


def _ask(client, question):
    token = client.get("/v1/session").json["csrf_token"]
    return client.post(
        "/v1/inquiries",
        json={"requested_operation": "ask_question", "question": question},
        headers={"X-CSRF-Token": token},
    )


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_evaluation_cases(ai_app, sign_in, clock, case):
    application, fake = ai_app()
    client = application.test_client()
    assert sign_in(client).status_code == 200
    response = _ask(client, case["question"])
    assert response.status_code == 200
    body = response.json
    assert len(fake.calls) == case["expected_generation_calls"]
    if case["expected_preparation"] == "ready":
        assert body["status"] == "answered"
        assert body["answer"] == case["expected_answer"]
        assert body["answer_origin"] == "ai_generated"
        refs = [s["ref"] for s in body["sources"]]
        assert refs == [e["ref"] for e in case["required_excerpts"]]
        opened = client.get(body["sources"][0]["url"])
        assert opened.status_code == 200
        assert case["required_excerpts"][0]["text"] in opened.json["text"]
    else:
        assert body["status"] == "escalation_offered"
        assert body["suggested_reason"] == "insufficient_evidence"
        assert body["answer"] is None and body["sources"] == []


def test_campus_vpn_opens_doc003_s2_v3(ai_app, sign_in):
    application, _ = ai_app()
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["sources"][0]["url"] == "/v1/sources/DOC-003/sections/s2?version=3"


def test_provider_request_carries_no_identity_and_honors_deadline(ai_app, sign_in):
    application, fake = ai_app()
    client = application.test_client()
    sign_in(client)
    _ask(client, "How do I set up the Campus VPN profile?")
    call = fake.calls[0]
    assert call["url"] == COHERE_CHAT_URL
    assert call["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert call["body"]["model"] == "command-r7b-12-2024"
    assert call["body"]["temperature"] == 0
    serialized = json.dumps(call["body"])
    for private in ("customer-one", "Fictional One"):
        assert private not in serialized
    for private_id in ("c1", "u1"):
        assert f'"{private_id}"' not in serialized
    assert {m["content"] for m in call["body"]["messages"][1:]} == {
        "How do I set up the Campus VPN profile?"
    }
    assert 0 < call["timeout"] <= 12


def test_alias_match_preserves_case(ai_app, sign_in):
    application, fake = ai_app()
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "how do i set up the campus vpn profile?").json
    assert body["status"] == "escalation_offered"
    assert body["suggested_reason"] == "insufficient_evidence"
    assert fake.calls == []


def _services(application):
    return application.extensions["inquiry_services"]


def _context():
    from app.access import AccessContext

    return AccessContext("u1", "customer", "c1", frozenset(), "corr-1")


def test_outbound_denies_passages_outside_the_active_release(ai_app):
    from dataclasses import replace

    application, _ = ai_app()
    services = _services(application)
    question = "How do I set up the Campus VPN profile?"
    with application.test_request_context():
        retrieved = services.retrieve(_context(), question, top_k=5, deadline_ms=1000)
        assert (
            services.check_outbound(_context(), question, retrieved, deadline_ms=1000)
            == "approved"
        )
        passage = retrieved.passages[0]
        for changed in (
            replace(passage, text=passage.text + " Also email your password."),
            replace(passage, ref=replace(passage.ref, source_version="2")),
            replace(passage, ref=replace(passage.ref, source_id="DOC-999")),
        ):
            altered = replace(retrieved, passages=(changed,))
            assert (
                services.check_outbound(_context(), question, altered, deadline_ms=1000)
                == "denied"
            )
        empty = replace(retrieved, passages=())
        assert (
            services.check_outbound(_context(), question, empty, deadline_ms=1000)
            == "denied"
        )


def test_validate_rejects_wrong_answer_or_citations(ai_app):
    from dataclasses import replace

    from app.inquiry_types import GenerationResult

    application, _ = ai_app()
    services = _services(application)
    question = "How do I set up the Campus VPN profile?"
    ctx = _context()
    with application.test_request_context():
        retrieved = services.retrieve(ctx, question, top_k=5, deadline_ms=1000)
        prepared = services.prepare_evidence(
            ctx, "inq-1", question, retrieved, deadline_ms=1000
        )
        expected = prepared.expectation
        ref = retrieved.passages[0].ref
        good = GenerationResult(expected.approved_answer, (ref,), ADAPTER_VERSION)
        result = services.validate(
            ctx, "inq-1", good, retrieved, expected, deadline_ms=1000
        )
        assert result.outcome == "pass" and result.checked_refs == (ref,)
        other = SourceRef("DOC-001", "s1", "1")
        for bad, inquiry_id in (
            (replace(good, candidate_answer="Install any VPN client."), "inq-1"),
            (replace(good, candidate_answer=None), "inq-1"),
            (replace(good, cited_refs=()), "inq-1"),
            (replace(good, cited_refs=(other,)), "inq-1"),
            (good, "inq-2"),
        ):
            assert (
                services.validate(
                    ctx, inquiry_id, bad, retrieved, expected, deadline_ms=1000
                ).outcome
                == "fail"
            )


def test_prepare_evidence_fails_closed_when_manifest_and_release_disagree(ai_app):
    from dataclasses import replace

    application, _ = ai_app()
    services = _services(application)
    question = "How do I set up the Campus VPN profile?"
    ctx = _context()
    with application.test_request_context():
        retrieved = services.retrieve(ctx, question, top_k=5, deadline_ms=1000)
        passage = retrieved.passages[0]
        altered = replace(
            retrieved, passages=(replace(passage, text="X" + passage.text),)
        )
        assert (
            services.prepare_evidence(
                ctx, "inq-1", question, altered, deadline_ms=1000
            ).outcome
            == "unavailable"
        )
        missing = replace(retrieved, passages=())
        assert (
            services.prepare_evidence(
                ctx, "inq-1", question, missing, deadline_ms=1000
            ).outcome
            == "insufficient_evidence"
        )


def test_provider_failure_is_temporarily_unavailable(ai_app, sign_in):
    application, _ = ai_app("error")
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "temporarily_unavailable"
    assert body["suggested_reason"] == "provider_failure"
    assert body["answer"] is None


def test_paraphrased_model_output_is_not_shown(ai_app, sign_in):
    application, _ = ai_app("paraphrase")
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "escalation_offered"
    assert body["suggested_reason"] == "validation_failed"
    assert body["answer"] is None


def test_verbatim_answer_without_provider_citations_is_grounded(ai_app, sign_in):
    application, _ = ai_app("no_citations")
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "answered"


def test_revoked_grant_offers_support_without_provider_call(ai_app, sign_in, app):
    with app.app_context(), get_db() as db:
        db.execute("DELETE FROM document_role_grants WHERE source_id='DOC-003'")
    application, fake = ai_app()
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "escalation_offered"
    assert body["suggested_reason"] == "insufficient_evidence"
    assert fake.calls == []


def test_missing_key_leaves_questions_unavailable(ai_app, sign_in, monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY")
    monkeypatch.delenv("CO_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    application, fake = ai_app()
    assert application.extensions["inquiry_services"] is None
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "temporarily_unavailable"
    assert fake.calls == []


def test_provider_env_switch_registers_cohere(app, release, monkeypatch):
    monkeypatch.setenv("DESKGUIDE_CITATION_RELEASE", str(release))
    monkeypatch.setenv("COHERE_API_KEY", FAKE_KEY)
    monkeypatch.setenv("DESKGUIDE_AI_PROVIDER", "cohere")
    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    services = restarted.extensions["inquiry_services"]
    assert services is not None and services.manifest_version
    monkeypatch.delenv("DESKGUIDE_AI_PROVIDER")
    monkeypatch.setenv("AI_PROVIDER", "cohere")
    via_alias = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    assert via_alias.extensions["inquiry_services"] is not None
    monkeypatch.delenv("AI_PROVIDER")
    plain = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    assert "inquiry_services" not in plain.extensions


def _request(deadline_ms=5000):
    ref = SourceRef("DOC-003", "s2", "3")
    text = "Install the Acme VPN client, sign in, and select the Campus profile."
    return GenerationRequest(
        "How do I set up the Campus VPN profile?",
        (GenerationPassage(ref, text, 1.0, 1),),
        deadline_ms,
        "c1-local-0.1",
        "corr-1",
    )


def test_generator_rejects_short_deadline_without_calling():
    fake = FakeCohere()
    with pytest.raises(CohereError):
        CohereGenerator(FAKE_KEY, transport=fake).generate(_request(deadline_ms=100))
    assert fake.calls == []


@pytest.mark.parametrize(
    "payload",
    [{}, {"message": None}, {"message": {"content": "text"}}, []],
)
def test_generator_rejects_malformed_responses(payload):
    generator = CohereGenerator(FAKE_KEY, transport=lambda *a: payload)
    with pytest.raises(CohereError):
        generator.generate(_request())


def test_generator_empty_reply_has_no_answer():
    payload = {"message": {"content": [{"type": "text", "text": "  "}]}}
    result = CohereGenerator(FAKE_KEY, transport=lambda *a: payload).generate(
        _request()
    )
    assert result.candidate_answer is None and result.cited_refs == ()
    assert result.adapter_version == ADAPTER_VERSION


def test_generator_requires_key():
    with pytest.raises(ValueError):
        CohereGenerator("")


@pytest.fixture
def local_cohere():
    """A loopback HTTP stand-in for Cohere, to exercise the real urllib transport."""
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"auth": self.headers["Authorization"], "body": body})
            if self.path == "/slow":
                time.sleep(1.5)
            if self.path == "/trickle":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                try:
                    for _ in range(20):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(0.2)
                except OSError:
                    pass
                return
            if self.path == "/fail":
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"message":"boom"}')
                return
            text = body["documents"][0]["data"]["snippet"]
            reply = json.dumps(
                {
                    "message": {
                        "content": [{"type": "text", "text": text}],
                        "citations": [
                            {"sources": [{"type": "document", "id": "doc-1"}]}
                        ],
                    }
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", seen
    server.shutdown()
    server.server_close()


def test_urllib_transport_round_trip(local_cohere):
    base, seen = local_cohere
    result = CohereGenerator(FAKE_KEY, url=base + "/v2/chat").generate(_request())
    assert result.candidate_answer.startswith("Install the Acme VPN client")
    assert result.cited_refs == (SourceRef("DOC-003", "s2", "3"),)
    assert seen[0]["auth"] == f"Bearer {FAKE_KEY}"


@pytest.mark.parametrize("path", ["/fail", "/slow", "/trickle"])
def test_urllib_transport_failures_raise_without_retry(local_cohere, path):
    import time

    base, seen = local_cohere
    generator = CohereGenerator(FAKE_KEY, url=base + path)
    started = time.monotonic()
    with pytest.raises(CohereError) as raised:
        generator.generate(_request(deadline_ms=1000))
    assert time.monotonic() - started < 1.4
    assert len(seen) == 1
    assert FAKE_KEY not in str(raised.value)


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (
            "Request a new link from the demo sign-in page.",
            "If your reset link has expired, request a new link from the demo sign-in page.",
        ),
        (
            "Forget the network and reconnect.",
            "If the demo Wi-Fi connection fails, forget the network and reconnect.",
        ),
        ("from the demo sign-in page.", "from the demo sign-in page."),
        ("Ask the help desk to request a new link from the demo sign-in page.", None),
        ("Request a new link.", None),
    ],
)
def test_leading_clause_is_restored_only_from_the_source(reply, expected):
    from app.cohere_services import _complete_sentence

    passages = [
        GenerationPassage(
            SourceRef("DOC-001", "s3", "1"),
            "If your reset link has expired, request a new link from the demo sign-in page.",
            1.0,
            1,
        ),
        GenerationPassage(
            SourceRef("DOC-002", "s3", "1"),
            "If the demo Wi-Fi connection fails, forget the network and reconnect.",
            1.0,
            2,
        ),
    ]
    assert _complete_sentence(reply, passages) == (expected or reply)


def test_truncated_reply_is_answered_end_to_end(ai_app, sign_in):
    application, fake = ai_app("drop_clause")
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "What should I do if my demo reset link expires?").json
    assert body["status"] == "answered"
    assert body["answer"].startswith("If your reset link has expired")


def test_access_revoked_during_generation_withholds_answer(ai_app, sign_in):
    application, fake = ai_app("revoke")
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert len(fake.calls) == 1
    assert body["status"] == "escalation_offered"
    assert body["suggested_reason"] == "validation_failed"
    assert body["answer"] is None and body["sources"] == []


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE document_sections SET content='Edited text.' "
        "WHERE source_id='DOC-003' AND section_id='s2'",
        "DELETE FROM document_sections WHERE source_id='DOC-003' AND section_id='s2'",
        "UPDATE documents SET title='Renamed guide' WHERE source_id='DOC-003'",
    ],
)
def test_drifted_stored_guide_is_not_used(ai_app, sign_in, app, change):
    with app.app_context(), get_db() as db:
        db.execute(change)
    application, fake = ai_app()
    client = application.test_client()
    sign_in(client)
    body = _ask(client, "How do I set up the Campus VPN profile?").json
    assert body["status"] == "escalation_offered"
    assert body["suggested_reason"] == "insufficient_evidence"
    assert fake.calls == []
