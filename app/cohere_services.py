"""Alpha inquiry services: exact-alias retrieval over the verified release and Cohere generation.

Retrieval, evidence preparation, outbound policy and validation run locally
against the hashed citation release that Flask verified at startup. Only the
generation step calls Cohere, and it receives the question and the permitted
passages, never customer identity or session data.
"""

import http.client
import json
import os
import re
import time
import unicodedata
import urllib.parse
from collections.abc import Callable

from flask import Flask

from .access import AccessContext
from .citation_release import parse_release, stored_guide
from .db import get_db
from .inquiry_types import (
    EvidenceExcerpt,
    EvidenceExpectation,
    EvidencePreparation,
    GenerationRequest,
    GenerationResult,
    Passage,
    RetrievalResult,
    SourceRef,
    ValidationResult,
)

COHERE_CHAT_URL = "https://api.cohere.com/v2/chat"
DEFAULT_MODEL = "command-r7b-12-2024"


SYSTEM_PROMPT = (
    "You answer IT help-desk questions using only the supplied documents. "
    "Reply with the one complete sentence from a document that answers the "
    "question, copied exactly from its first word to its final period. Keep "
    "any opening clause, such as one beginning with 'If', and do not shorten, "
    "reword or add to the sentence. If no document answers the question, "
    "reply with nothing."
)
ADAPTER_VERSION = "cohere-chat-v2-extractive-2"


def normalized_question(text: str) -> str:
    """NFC plus trimmed, collapsed whitespace; case and punctuation are kept."""
    return " ".join(unicodedata.normalize("NFC", text).split())


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _complete_sentence(reply: str, passages) -> str:
    """Restore a source sentence when the model copied only its ending.

    The model sometimes drops a leading clause ("If ..., request a new link"
    becomes "Request a new link"). When the reply, apart from its first
    letter's case, is the exact ending of exactly one supplied sentence, return
    that whole sentence. Anything else is returned unchanged for validation.
    """
    answer = normalized_question(reply)
    # Only a capitalized reply that keeps most of the sentence is expanded.
    if len(answer) < 12 or not answer[:1].isupper():
        return reply
    matches = set()
    for passage in passages:
        for sentence in _SENTENCE_END.split(normalized_question(passage.text)):
            if sentence == answer:
                return reply
            tail = sentence[len(sentence) - len(answer) :]
            if (
                len(sentence) > len(answer)
                and len(answer) * 10 >= len(sentence) * 4
                and tail[1:] == answer[1:]
                and tail[:1].casefold() == answer[:1].casefold()
                and sentence[len(sentence) - len(answer) - 1] == " "
            ):
                matches.add(sentence)
    return matches.pop() if len(matches) == 1 else reply


class CohereError(Exception):
    """Raised for any provider failure; the message never contains private input."""


Transport = Callable[[str, dict, dict, float], dict]


MAX_RESPONSE_BYTES = 256 * 1024


def _urllib_transport(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """POST with one wall-clock deadline across connect, send and every read."""
    deadline = time.monotonic() + timeout

    def remaining():
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError
        return left

    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise CohereError("Cohere request failed.")
    connection_type = (
        http.client.HTTPSConnection
        if parts.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_type(parts.hostname, parts.port, timeout=remaining())
    try:
        connection.connect()
        # Keep our own handle: http.client drops connection.sock once a response
        # will close the connection, but the response keeps reading from it.
        sock = connection.sock
        sock.settimeout(remaining())
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        connection.request("POST", path, json.dumps(body).encode(), headers)
        sock.settimeout(remaining())
        response = connection.getresponse()
        chunks, size = [], 0
        while not response.isclosed():
            sock.settimeout(remaining())
            chunk = response.read1(16384)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise CohereError("Cohere returned an oversized response.")
            chunks.append(chunk)
        remaining()
        if response.status != 200:
            raise CohereError(f"Cohere returned HTTP {response.status}.")
        return json.loads(b"".join(chunks))
    except CohereError:
        raise
    except (OSError, http.client.HTTPException, ValueError):
        # TimeoutError is an OSError; never include provider or request text.
        raise CohereError("Cohere request failed.") from None
    finally:
        connection.close()


class CohereGenerator:
    """One Cohere Chat v2 call per request, bounded by the supplied deadline, no retries."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        url: str = COHERE_CHAT_URL,
        transport: Transport = _urllib_transport,
    ):
        if not api_key:
            raise ValueError("A Cohere API key is required.")
        self._api_key = api_key
        self.model = model
        self._url = url
        self._transport = transport

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.deadline_ms < 500 or not request.passages:
            raise CohereError("Not enough time or evidence for a provider call.")
        documents = {}
        for index, passage in enumerate(request.passages, start=1):
            documents[f"doc-{index}"] = passage
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.question},
            ],
            "documents": [
                {"id": doc_id, "data": {"snippet": passage.text}}
                for doc_id, passage in documents.items()
            ],
            "temperature": 0,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Leave headroom so the coordinator's own deadline check still passes.
        timeout = max(0.1, (request.deadline_ms - 250) / 1000)
        payload = self._transport(self._url, headers, body, timeout)
        return self._parse(payload, documents)

    def _parse(self, payload, documents) -> GenerationResult:
        try:
            message = payload["message"]
            text = "".join(
                part["text"]
                for part in message.get("content") or ()
                if part.get("type") == "text"
            ).strip()
            citations = message.get("citations") or ()
            cited_ids = {
                source["id"]
                for citation in citations
                for source in citation.get("sources") or ()
                if source.get("type", "document") == "document"
            }
        except (KeyError, TypeError, AttributeError):
            raise CohereError("Cohere returned an unexpected response.") from None
        if not text:
            return GenerationResult(None, (), ADAPTER_VERSION)
        text = _complete_sentence(text, documents.values())
        refs = [documents[i].ref for i in documents if i in cited_ids]
        # Ground the answer in any supplied passage that contains it word for word.
        answer = normalized_question(text)
        for passage in documents.values():
            if passage.ref not in refs and answer in normalized_question(passage.text):
                refs.append(passage.ref)
        return GenerationResult(text, tuple(refs), ADAPTER_VERSION)


class ReleaseInquiryServices:
    """InquiryServices over the verified release; generation is delegated."""

    def __init__(self, app: Flask, generator):
        release = app.config["CITATION_RELEASE"]
        manifest = app.extensions["citation_release_manifest"]
        content = app.extensions["citation_release_content"]
        current, _, _ = parse_release(release)
        self._generator = generator
        self.manifest_version = str(manifest.get("manifest_version") or "unversioned")
        self.policy_version = str(manifest.get("policy_version") or "unversioned")
        # (source_id, version) -> (digest, title, sections) for active pins only.
        self._current = {}
        for source_id, (version, digest) in current.items():
            title, sections = content[source_id, version, digest]
            self._current[source_id] = (version, digest, title, sections)
        self._intents = {}
        for intent in manifest.get("intents") or ():
            for alias in intent.get("aliases") or ():
                key = normalized_question(alias)
                if key in self._intents:
                    raise ValueError("Duplicate normalized alias in the manifest.")
                self._intents[key] = intent

    def _permitted_sources(self, ctx: AccessContext, source_ids) -> set[str]:
        """Apply citation lookup's grant and stored-content checks to current pins.

        A source is admitted only if its citation would open right now: the
        caller holds a current grant, the document is active, and the stored
        title and complete section set still match the verified snapshot.
        """
        permitted = set()
        db = get_db()
        for source_id in source_ids:
            if source_id not in self._current:
                continue
            version, digest, title, sections = self._current[source_id]
            row = db.execute(
                """
                SELECT 1
                FROM documents AS d
                JOIN document_versions AS v
                  ON v.source_id = d.source_id AND v.source_version = ?
                JOIN document_role_grants AS grant
                  ON grant.source_id = d.source_id AND grant.role = ?
                WHERE d.source_id = ? AND d.state = 'active' AND v.content_hash = ?
                  AND (grant.role != 'customer'
                       OR NOT EXISTS (
                           SELECT 1 FROM document_customer_grants AS cg
                           WHERE cg.source_id = d.source_id
                       )
                       OR EXISTS (
                           SELECT 1 FROM document_customer_grants AS cg
                           WHERE cg.source_id = d.source_id AND cg.customer_id = ?
                       ))
                """,
                (version, ctx.role, source_id, digest, ctx.customer_scope),
            ).fetchone()
            if row is not None and stored_guide(db, source_id, version) == (
                title,
                dict(sections),
            ):
                permitted.add(source_id)
        return permitted

    def _intent_refs(self, intent):
        refs = []
        for excerpt in intent.get("required_excerpts") or ():
            ref = excerpt.get("ref") or {}
            refs.append(
                SourceRef(
                    str(ref.get("source_id")),
                    str(ref.get("section_id")),
                    str(ref.get("source_version")),
                )
            )
        return refs

    def retrieve(
        self, ctx: AccessContext, question: str, *, top_k: int, deadline_ms: int
    ) -> RetrievalResult:
        intent = self._intents.get(normalized_question(question))
        if intent is None:
            return RetrievalResult((), self.manifest_version)
        refs = self._intent_refs(intent)
        active = [
            ref
            for ref in refs
            if ref.source_id in self._current
            and str(self._current[ref.source_id][0]) == ref.source_version
            and ref.section_id in self._current[ref.source_id][3]
        ]
        permitted = self._permitted_sources(ctx, {ref.source_id for ref in active})
        passages = []
        for ref in active:
            if ref.source_id not in permitted or len(passages) >= top_k:
                continue
            _, _, title, sections = self._current[ref.source_id]
            heading, text = sections[ref.section_id]
            passages.append(
                Passage(ref, text, title, heading, score=1.0, rank=len(passages) + 1)
            )
        return RetrievalResult(tuple(passages), self.manifest_version)

    def prepare_evidence(
        self,
        ctx: AccessContext,
        inquiry_id: str,
        question: str,
        retrieved: RetrievalResult,
        *,
        deadline_ms: int,
    ) -> EvidencePreparation:
        intent = self._intents.get(normalized_question(question))
        if intent is None:
            return EvidencePreparation("insufficient_evidence")
        texts = {
            p.ref: unicodedata.normalize("NFC", p.text) for p in retrieved.passages
        }
        excerpts = []
        for ref, excerpt in zip(
            self._intent_refs(intent),
            intent.get("required_excerpts") or (),
            strict=True,
        ):
            text = texts.get(ref)
            start, end, quoted = (
                excerpt.get("start"),
                excerpt.get("end"),
                excerpt.get("text"),
            )
            if text is None:
                return EvidencePreparation("insufficient_evidence")
            if (
                type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(text)
                or text[start:end] != quoted
            ):
                # The verified release disagrees with the manifest: fail closed.
                return EvidencePreparation("unavailable")
            excerpts.append(EvidenceExcerpt(ref, start, end, quoted))
        if not excerpts:
            return EvidencePreparation("insufficient_evidence")
        return EvidencePreparation(
            "ready",
            EvidenceExpectation(
                inquiry_id,
                self.policy_version,
                self.manifest_version,
                str(intent.get("intent_id")),
                str(intent.get("approved_answer")),
                tuple(excerpts),
            ),
        )

    def check_outbound(
        self,
        ctx: AccessContext,
        question: str,
        retrieved: RetrievalResult,
        *,
        deadline_ms: int,
    ) -> str:
        # Only verified synthetic guides at their active pins may leave the server.
        for passage in retrieved.passages:
            pin = self._current.get(passage.ref.source_id)
            if pin is None or str(pin[0]) != passage.ref.source_version:
                return "denied"
            if pin[3].get(passage.ref.section_id, (None, None))[1] != passage.text:
                return "denied"
        return "approved" if retrieved.passages else "denied"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return self._generator.generate(request)

    def validate(
        self,
        ctx: AccessContext,
        inquiry_id: str,
        candidate: GenerationResult,
        retrieved: RetrievalResult,
        expectation: EvidenceExpectation,
        *,
        deadline_ms: int,
    ) -> ValidationResult:
        if not isinstance(candidate.candidate_answer, str):
            return ValidationResult("fail")
        answer = normalized_question(candidate.candidate_answer)
        passages = {p.ref: p for p in retrieved.passages}
        cited = tuple(dict.fromkeys(candidate.cited_refs))
        required = {e.ref for e in expectation.required_excerpts}
        if (
            expectation.inquiry_id != inquiry_id
            or answer != normalized_question(expectation.approved_answer)
            or not cited
            or not set(cited) <= passages.keys()
            or not required <= set(cited)
            or not all(
                normalized_question(e.text) in answer
                or answer in normalized_question(e.text)
                for e in expectation.required_excerpts
            )
        ):
            return ValidationResult("fail")
        # Access or stored content may have changed while the provider ran.
        if any(
            ref.source_id not in self._current
            or str(self._current[ref.source_id][0]) != ref.source_version
            for ref in cited
        ):
            return ValidationResult("fail")
        sources = {ref.source_id for ref in cited}
        if self._permitted_sources(ctx, sources) != sources:
            return ValidationResult("fail")
        return ValidationResult("pass", cited)


def build_inquiry_services(app: Flask, *, transport: Transport | None = None):
    """Factory for create_app(); returns None (AI unavailable) without a key."""
    api_key = (
        os.environ.get("COHERE_API_KEY")
        or os.environ.get("CO_API_KEY")
        or os.environ.get("AI_API_KEY")
    )
    if not api_key:
        app.logger.warning("Cohere is not configured; questions stay unavailable.")
        return None
    model = (
        os.environ.get("DESKGUIDE_COHERE_MODEL")
        or os.environ.get("AI_MODEL")
        or DEFAULT_MODEL
    )
    kwargs = {"model": model}
    if transport is not None:
        kwargs["transport"] = transport
    try:
        return ReleaseInquiryServices(app, CohereGenerator(api_key, **kwargs))
    except (KeyError, ValueError, TypeError):
        app.logger.warning("Inquiry services could not load the verified release.")
        return None
