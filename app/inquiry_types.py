"""Immutable integration types for the inquiry coordinator and its dependencies."""

from dataclasses import dataclass
from typing import Protocol

from .access import AccessContext


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_id: str
    section_id: str
    source_version: str


@dataclass(frozen=True, slots=True)
class Passage:
    ref: SourceRef
    text: str
    title: str
    section_title: str
    score: float = 1.0
    rank: int = 1


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    passages: tuple[Passage, ...]
    index_version: str


@dataclass(frozen=True, slots=True)
class EvidenceExcerpt:
    ref: SourceRef
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class EvidenceExpectation:
    inquiry_id: str
    policy_version: str
    manifest_version: str
    intent_id: str
    approved_answer: str
    required_excerpts: tuple[EvidenceExcerpt, ...]


@dataclass(frozen=True, slots=True)
class EvidencePreparation:
    outcome: str
    expectation: EvidenceExpectation | None = None


@dataclass(frozen=True, slots=True)
class GenerationPassage:
    ref: SourceRef
    text: str
    score: float
    rank: int


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    question: str
    passages: tuple[GenerationPassage, ...]
    deadline_ms: int
    configuration_version: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    candidate_answer: str | None
    cited_refs: tuple[SourceRef, ...]
    adapter_version: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    outcome: str
    checked_refs: tuple[SourceRef, ...] = ()


class InquiryServices(Protocol):
    """Internal adapters must enforce their supplied timeout without retries."""

    def retrieve(
        self, ctx: AccessContext, question: str, *, top_k: int, deadline_ms: int
    ) -> RetrievalResult: ...

    def prepare_evidence(
        self,
        ctx: AccessContext,
        inquiry_id: str,
        question: str,
        retrieved: RetrievalResult,
        *,
        deadline_ms: int,
    ) -> EvidencePreparation: ...

    def check_outbound(
        self,
        ctx: AccessContext,
        question: str,
        retrieved: RetrievalResult,
        *,
        deadline_ms: int,
    ) -> str:
        """Return approved, denied or unavailable; labels from clients are not authority."""
        ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def validate(
        self,
        ctx: AccessContext,
        inquiry_id: str,
        candidate: GenerationResult,
        retrieved: RetrievalResult,
        expectation: EvidenceExpectation,
        *,
        deadline_ms: int,
    ) -> ValidationResult: ...
