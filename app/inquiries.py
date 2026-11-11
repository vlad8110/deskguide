"""C1 inquiry routing, evidence gates, controlled fallback and minimal metadata."""

import math
import time
import unicodedata
from dataclasses import asdict
from urllib.parse import quote
from uuid import uuid4

from flask import Blueprint, current_app, g, jsonify, request

from .access import current_access, require_roles
from .clock import now
from .db import get_db
from .errors import CONTRACT_VERSION, ApiError
from .inquiry_types import (
    EvidenceExpectation,
    EvidencePreparation,
    GenerationPassage,
    GenerationRequest,
    GenerationResult,
    RetrievalResult,
    SourceRef,
    ValidationResult,
)

bp = Blueprint("inquiries", __name__, url_prefix="/v1/inquiries")


def _normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def _validate_request(payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "VALIDATION_FAILED", "Provide an inquiry object.")
    operation = payload.get("requested_operation")
    if operation not in ("ask_question", "check_account_status"):
        raise ApiError(400, "VALIDATION_FAILED", "Choose a supported operation.")
    # Conversation storage is not part of this slice; never accept an unverified ID.
    if payload.get("conversation_id") is not None:
        raise ApiError(403, "FORBIDDEN", "This conversation is unavailable.")
    if operation == "check_account_status":
        if "question" in payload:
            raise ApiError(400, "VALIDATION_FAILED", "Do not include a question here.")
        return operation, None
    question = payload.get("question")
    if not isinstance(question, str) or any(
        unicodedata.category(c) in {"Cc", "Cs"} for c in question
    ):
        raise ApiError(400, "VALIDATION_FAILED", "Provide a question without controls.")
    question = unicodedata.normalize("NFC", question.strip())
    if not 1 <= len(question) <= 1000:
        raise ApiError(400, "VALIDATION_FAILED", "Use between 1 and 1000 characters.")
    return operation, question


def _admit(context, route, configuration):
    connection = get_db()
    current = now()
    inquiry_id = str(uuid4())
    connection.execute("BEGIN IMMEDIATE")
    try:
        active = connection.execute(
            "SELECT COUNT(*) FROM inquiries WHERE outcome='processing' AND created_at>?",
            (current - 20,),
        ).fetchone()[0]
        own = connection.execute(
            "SELECT created_at,outcome FROM inquiries WHERE customer_id=? AND created_at>?",
            (context.customer_scope, current - 60),
        ).fetchall()
        if any(
            r["outcome"] == "processing" and r["created_at"] > current - 20 for r in own
        ):
            raise ApiError(
                429,
                "RATE_LIMITED",
                "Wait for your current inquiry.",
                retryable=True,
                retry_after=1,
            )
        if len(own) >= 5:
            raise ApiError(
                429,
                "RATE_LIMITED",
                "Please wait before asking again.",
                retryable=True,
                retry_after=max(1, min(r["created_at"] for r in own) + 60 - current),
            )
        if active >= current_app.config["INQUIRY_MAX_ACTIVE"]:
            raise ApiError(
                503,
                "SERVICE_BUSY",
                "DeskGuide is busy. Please try again shortly.",
                retryable=True,
                retry_after=1,
            )
        connection.execute(
            "INSERT INTO inquiries (inquiry_id,customer_id,route,outcome,"
            "configuration_version,created_at,expires_at) VALUES (?,?,?,'processing',?,?,?)",
            (
                inquiry_id,
                context.customer_scope,
                route,
                configuration,
                current,
                current + 30 * 86400,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return inquiry_id


class InquiryDeadlineExceeded(ApiError):
    pass


class Deadline:
    def __init__(self):
        self.clock = current_app.config["INQUIRY_MONOTONIC"]
        self.end = self.clock() + 20

    def budget(self, maximum=19000):
        remaining = self.end - self.clock()
        if remaining <= 0:
            raise InquiryDeadlineExceeded(
                504,
                "DEADLINE_EXCEEDED",
                "This took too long. Try again.",
                retryable=True,
            )
        return max(0, min(maximum, int((remaining - 1) * 1000)))

    def run(self, maximum, callback):
        budget = self.budget(maximum)
        if not budget:
            raise TimeoutError
        started = self.clock()
        result = callback(budget)
        self.budget()
        if (self.clock() - started) * 1000 >= budget:
            raise TimeoutError
        return result


def _valid_retrieval(result):
    if not isinstance(result, RetrievalResult) or not isinstance(
        result.passages, tuple
    ):
        return False
    if (
        not isinstance(result.index_version, str)
        or not result.index_version
        or len(result.passages) > 8
    ):
        return False
    refs = set()
    for p in result.passages:
        if not isinstance(p.ref, SourceRef) or any(
            not isinstance(v, str)
            or not 1 <= len(v) <= 200
            or any(unicodedata.category(c) in {"Cc", "Cs"} for c in v)
            for v in (p.ref.source_id, p.ref.section_id, p.ref.source_version)
        ):
            return False
        if p.ref in refs or not isinstance(p.text, str) or not 1 <= len(p.text) <= 1500:
            return False
        if (
            not isinstance(p.title, str)
            or not 1 <= len(p.title) <= 200
            or not isinstance(p.section_title, str)
            or not 1 <= len(p.section_title) <= 200
        ):
            return False
        if (
            not isinstance(p.score, (int, float))
            or not math.isfinite(p.score)
            or not 0 <= p.score <= 1
            or type(p.rank) is not int
            or p.rank < 1
        ):
            return False
        refs.add(p.ref)
    return True


def _valid_expectation(expected, inquiry_id, retrieved):
    if (
        not isinstance(expected, EvidenceExpectation)
        or expected.inquiry_id != inquiry_id
    ):
        return False
    if (
        any(
            not isinstance(v, str) or not v
            for v in (
                expected.policy_version,
                expected.manifest_version,
                expected.intent_id,
                expected.approved_answer,
            )
        )
        or len(expected.approved_answer) > 4000
    ):
        return False
    if (
        not isinstance(expected.required_excerpts, tuple)
        or not expected.required_excerpts
    ):
        return False
    passages = {p.ref: unicodedata.normalize("NFC", p.text) for p in retrieved.passages}
    for excerpt in expected.required_excerpts:
        text = passages.get(excerpt.ref)
        if (
            text is None
            or type(excerpt.start) is not int
            or type(excerpt.end) is not int
        ):
            return False
        if (
            not 0 <= excerpt.start < excerpt.end <= len(text)
            or text[excerpt.start : excerpt.end] != excerpt.text
        ):
            return False
    return True


def _run_ai(context, inquiry_id, question, configuration, deadline):
    services = current_app.extensions.get("inquiry_services")
    if services is None:
        return "temporarily_unavailable", "service_unavailable", None, []
    reason = "service_unavailable"
    try:
        retrieved = deadline.run(
            2000,
            lambda budget: services.retrieve(
                context, question, top_k=5, deadline_ms=budget
            ),
        )
        if not deadline.budget() or not _valid_retrieval(retrieved):
            return "temporarily_unavailable", reason, None, []
        preparation = deadline.run(
            19000,
            lambda budget: services.prepare_evidence(
                context, inquiry_id, question, retrieved, deadline_ms=budget
            ),
        )
        if not deadline.budget() or not isinstance(preparation, EvidencePreparation):
            return "temporarily_unavailable", reason, None, []
        if preparation.outcome == "insufficient_evidence":
            return "escalation_offered", "insufficient_evidence", None, []
        expected = preparation.expectation
        if preparation.outcome != "ready" or not _valid_expectation(
            expected, inquiry_id, retrieved
        ):
            return "temporarily_unavailable", reason, None, []
        outbound = deadline.run(
            19000,
            lambda budget: services.check_outbound(
                context, question, retrieved, deadline_ms=budget
            ),
        )
        if not deadline.budget() or outbound not in {"approved", "denied"}:
            return "temporarily_unavailable", reason, None, []
        if outbound == "denied":
            return "escalation_offered", "insufficient_evidence", None, []
        reason = "provider_failure"
        candidate = deadline.run(
            12000,
            lambda budget: services.generate(
                GenerationRequest(
                    question,
                    tuple(
                        GenerationPassage(p.ref, p.text, p.score, p.rank)
                        for p in retrieved.passages
                    ),
                    budget,
                    configuration,
                    context.correlation_id,
                )
            ),
        )
        if not deadline.budget():
            return "temporarily_unavailable", reason, None, []
        reason = "validation_failed"
        if (
            not isinstance(candidate, GenerationResult)
            or not isinstance(candidate.candidate_answer, str)
            or not 1 <= len(candidate.candidate_answer) <= 4000
            or not isinstance(candidate.cited_refs, tuple)
        ):
            return "escalation_offered", reason, None, []
        available = {p.ref: p for p in retrieved.passages}
        cited = set(candidate.cited_refs)
        required = {excerpt.ref for excerpt in expected.required_excerpts}
        if (
            not cited
            or not cited <= available.keys()
            or not required <= cited
            or _normalized(candidate.candidate_answer)
            != _normalized(expected.approved_answer)
        ):
            return "escalation_offered", reason, None, []
        validation = deadline.run(
            19000,
            lambda budget: services.validate(
                context,
                inquiry_id,
                candidate,
                retrieved,
                expected,
                deadline_ms=budget,
            ),
        )
        if (
            not deadline.budget()
            or not isinstance(validation, ValidationResult)
            or validation.outcome != "pass"
            or set(validation.checked_refs) != cited
        ):
            return "escalation_offered", reason, None, []
        sources = []
        for p in retrieved.passages:
            if p.ref in cited:
                ref = p.ref
                sources.append(
                    {
                        "ref": asdict(ref),
                        "title": p.title,
                        "section_title": p.section_title,
                        "url": f"/v1/sources/{quote(ref.source_id, safe='')}/sections/{quote(ref.section_id, safe='')}?version={quote(ref.source_version, safe='')}",
                    }
                )
        return "answered", None, candidate.candidate_answer, sources
    except InquiryDeadlineExceeded:
        raise
    except Exception:
        # Dependency exceptions can contain private input; never log their text.
        current_app.logger.warning(
            "inquiry_dependency_failed correlation_id=%s", context.correlation_id
        )
        deadline.budget()
        status = (
            "escalation_offered"
            if reason == "validation_failed"
            else "temporarily_unavailable"
        )
        return status, reason, None, []


@bp.post("")
@require_roles("customer")
def submit():
    deadline = Deadline()
    operation, question = _validate_request(request.get_json(silent=True))
    context = current_access()
    configuration = current_app.config["INQUIRY_CONFIGURATION_VERSION"]
    route = "ai" if operation == "ask_question" else "account_status"
    inquiry_id = _admit(context, route, configuration)
    try:
        if route == "ai":
            status, reason, answer, sources = _run_ai(
                context, inquiry_id, question, configuration, deadline
            )
        else:
            # C7 is not connected yet; never infer account facts from question text.
            status, reason, answer, sources = (
                "escalation_offered",
                "service_unavailable",
                None,
                [],
            )
        deadline.budget()
        answer_id = str(uuid4()) if status == "answered" else None
        with get_db() as connection:
            connection.execute(
                "UPDATE inquiries SET outcome=?,answer_id=? WHERE inquiry_id=?",
                (status, answer_id, inquiry_id),
            )
    except Exception:
        with get_db() as connection:
            connection.execute(
                "UPDATE inquiries SET outcome='failed' WHERE inquiry_id=?",
                (inquiry_id,),
            )
        raise
    return jsonify(
        contract_version=CONTRACT_VERSION,
        inquiry_id=inquiry_id,
        answer_id=answer_id,
        status=status,
        route=route,
        answer_origin="ai_generated" if answer_id else None,
        answer=answer,
        sources=sources,
        clarification_prompt=None,
        escalation_offered=status in {"escalation_offered", "temporarily_unavailable"},
        suggested_reason=reason,
        configuration_version=configuration,
        correlation_id=g.correlation_id,
    )


def init_app(app):
    app.config.setdefault("INQUIRY_CONFIGURATION_VERSION", "c1-local-0.1")
    app.config.setdefault("INQUIRY_MAX_ACTIVE", 5)
    app.config.setdefault("INQUIRY_MONOTONIC", time.monotonic)
    app.register_blueprint(bp)
