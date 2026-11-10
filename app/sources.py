"""C2b citation lookup for approved source versions and current role grants."""

from dataclasses import asdict

from flask import Blueprint, current_app, g, jsonify, request

from .access import current_access
from .citation_release import (
    SECTION_ID,
    SOURCE_ID,
    parse_release,
    source_version,
    stored_guide,
)
from .clock import now
from .db import get_db
from .errors import CONTRACT_VERSION, ApiError
from .inquiry_types import SourceRef

bp = Blueprint("sources", __name__, url_prefix="/v1/sources")


def _unavailable():
    return ApiError(
        503,
        "DEPENDENCY_UNAVAILABLE",
        "Citation sources are temporarily unavailable.",
        retryable=True,
    )


@bp.get("/<source_id>/sections/<section_id>")
def get_section(source_id, section_id):
    context = current_access()
    versions = request.args.getlist("version")
    if (
        not SOURCE_ID.fullmatch(source_id)
        or not SECTION_ID.fullmatch(section_id)
        or len(versions) > 1
    ):
        raise ApiError(400, "VALIDATION_FAILED", "Provide a valid source reference.")

    try:
        requested = source_version(versions[0]) if versions else None
    except ValueError:
        raise ApiError(
            400, "VALIDATION_FAILED", "Provide a valid source version."
        ) from None

    release = current_app.config["CITATION_RELEASE"]
    if release is None:
        raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")
    try:
        current, historical, retired_until = parse_release(release)
    except ValueError:
        raise _unavailable() from None

    active_version, active_hash = current.get(source_id, (None, None))
    version = requested if requested is not None else active_version
    digest = (
        active_hash
        if version == active_version
        else historical.get(source_id, {}).get(version)
    )
    if digest is None:
        raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")

    section = (
        get_db()
        .execute(
            """
            SELECT d.title AS document_title, s.title AS section_title, s.content,
                   v.content_hash
            FROM document_sections AS s
            JOIN documents AS d ON d.source_id = s.source_id
            JOIN document_versions AS v
              ON v.source_id = s.source_id AND v.source_version = s.source_version
            JOIN document_role_grants AS grant
              ON grant.source_id = d.source_id AND grant.role = ?
            WHERE s.source_id = ? AND s.section_id = ? AND s.source_version = ?
              AND (d.state = 'active' OR ?)
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
            (
                context.role,
                source_id,
                section_id,
                version,
                requested is not None and now() < retired_until.get(source_id, 0),
                context.customer_scope,
            ),
        )
        .fetchone()
    )
    if section is None:
        raise ApiError(404, "NOT_FOUND", "The requested item is unavailable.")
    expected = current_app.extensions.get("citation_release_content", {}).get(
        (source_id, version, digest)
    )
    if (
        section["content_hash"] != digest
        or expected is None
        or stored_guide(get_db(), source_id, version) != expected
        or (section["document_title"], section["section_title"], section["content"])
        != (expected[0], *expected[1].get(section_id, (None, None)))
    ):
        raise _unavailable()

    return jsonify(
        ref=asdict(SourceRef(source_id, section_id, str(version))),
        document_title=section["document_title"],
        section_title=section["section_title"],
        text=section["content"],
        correlation_id=g.correlation_id,
        contract_version=CONTRACT_VERSION,
    )
