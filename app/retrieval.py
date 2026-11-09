"""Draft C2 interface for scoped retrieval and exact citation lookup."""

from typing import Protocol

from .access import AccessContext
from .inquiry_types import Passage, RetrievalResult, SourceRef


class RetrievalAdapter(Protocol):
    """Use server-derived access and honor the supplied budget without retries."""

    def retrieve(
        self,
        ctx: AccessContext,
        question: str,
        *,
        top_k: int,
        deadline_ms: int,
    ) -> RetrievalResult:
        """Rank only permitted, approved passages and return at most top_k.

        No permitted matches is a successful result with an empty tuple.
        A timeout or dependency failure raises instead of returning no matches.
        """
        ...

    def lookup_exact(
        self,
        ctx: AccessContext,
        ref: SourceRef,
        *,
        deadline_ms: int,
    ) -> Passage | None:
        """Recheck access and resolve the exact source, section, and version.

        Return None for missing, retired, or inaccessible content. Never
        substitute a different version. Dependency failures raise.
        """
        ...
