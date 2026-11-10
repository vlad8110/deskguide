"""Load pinned citation releases and import reviewed fictional guides."""

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from types import MappingProxyType

import click
from flask.cli import with_appcontext

from .clock import now
from .db import get_db

SOURCE_ID = re.compile(r"DOC-[0-9]{3}")
SECTION_ID = re.compile(r"s[0-9]{1,2}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def source_version(value):
    if type(value) is int and 0 < value <= 2**63 - 1:
        return value
    if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,18}", value):
        return source_version(int(value))
    raise ValueError("Invalid source version.")


def _digest(value):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError("Expected a lowercase SHA-256 digest.")
    return value


def _mapping(value):
    if not isinstance(value, dict):
        raise ValueError("Expected a release object.")
    return value


def _sources(value):
    for source_id, item in _mapping(value).items():
        if not isinstance(source_id, str) or not SOURCE_ID.fullmatch(source_id):
            raise ValueError("Invalid release source ID.")
        yield source_id, item


def _pin(value):
    pin = _mapping(value)
    return source_version(pin.get("version")), _digest(pin.get("sha256"))


def parse_release(value):
    release = _mapping(value)
    _digest(release.get("manifest_sha256"))
    current = {
        source_id: _pin(pin) for source_id, pin in _sources(release.get("current"))
    }
    historical = {}
    for source_id, entries in _sources(release.get("historical", {})):
        if not isinstance(entries, list):
            raise ValueError("Expected a list of historical pins.")
        pins = {}
        for entry in entries:
            version, digest = _pin(entry)
            if version in pins or version == current.get(source_id, (None,))[0]:
                raise ValueError("Duplicate release pin.")
            pins[version] = digest
        historical[source_id] = pins
    retired_until = dict(_sources(release.get("retired_until", {})))
    if any(type(t) is not int or t < 0 for t in retired_until.values()):
        raise ValueError("Expected a UTC Unix retirement cutoff.")
    return current, historical, retired_until


def _read_pinned_json(path, digest):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f"Hash does not match for {path.name}.")
    return _mapping(json.loads(content))


def _read_release(path):
    release = _mapping(json.loads(path.read_bytes()))
    parse_release(release)
    manifest = _read_pinned_json(
        path.with_name("evidence_manifest.json"), release["manifest_sha256"]
    )
    if (
        manifest.get("review_status") != "approved"
        or manifest.get("runtime_enabled") is not True
    ):
        raise ValueError("The evidence manifest must be approved and enabled.")
    return release


def _guide(path, source_id, version, digest):
    guide = _read_pinned_json(path.with_name(f"{source_id}.v{version}.json"), digest)
    if (
        guide.get("source_id") != source_id
        or source_version(guide.get("source_version")) != version
        or guide.get("classification") != "synthetic"
        or guide.get("review_status") != "approved"
    ):
        raise ValueError(
            "Each pinned guide must match its reference and be approved fictional data."
        )
    title = guide.get("title")
    sections = guide.get("sections")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError("Invalid guide title.")
    if not isinstance(sections, list) or not 1 <= len(sections) <= 30:
        raise ValueError("Invalid guide sections.")
    rows = {}
    for item in sections:
        section = _mapping(item)
        section_id, heading, text = (
            section.get("section_id"),
            section.get("title"),
            section.get("text"),
        )
        if (
            not isinstance(section_id, str)
            or not SECTION_ID.fullmatch(section_id)
            or section_id in rows
            or not isinstance(heading, str)
            or not heading.strip()
            or not isinstance(text, str)
            or not 1 <= len(text) <= 5000
        ):
            raise ValueError("Invalid guide section.")
        rows[section_id] = (heading, text)
    return title, rows


def _release_pins(release):
    current, historical, _ = parse_release(release)
    pins = {
        source_id: {version: digest} for source_id, (version, digest) in current.items()
    }
    for source_id, versions in historical.items():
        pins.setdefault(source_id, {}).update(versions)
    return pins


def _verified_guides(path, release):
    """Keep reviewed file content outside the mutable source database."""
    guides = {}
    for source_id, versions in _release_pins(release).items():
        for version, digest in versions.items():
            title, sections = _guide(path, source_id, version, digest)
            guides[source_id, version, digest] = (title, MappingProxyType(sections))
    return MappingProxyType(guides)


def stored_guide(db, source_id, version):
    """Read the complete title and section set for an imported version."""
    document = db.execute(
        "SELECT title FROM documents WHERE source_id=?", (source_id,)
    ).fetchone()
    sections = db.execute(
        "SELECT section_id, title, content FROM document_sections "
        "WHERE source_id=? AND source_version=?",
        (source_id, version),
    ).fetchall()
    return (
        document["title"] if document else None,
        {row["section_id"]: (row["title"], row["content"]) for row in sections},
    )


@click.command("import-citation-release")
@click.argument(
    "release_file", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--grant-customer",
    "customer_sources",
    multiple=True,
    metavar="SOURCE_ID",
    help="Grant the customer role access to this current source. Repeat for each source.",
)
@with_appcontext
def import_citation_release(release_file, customer_sources):
    """Import the hashed guides in an approved fictional citation release."""
    try:
        release = _read_release(release_file)
        current, _, _ = parse_release(release)
        for source_id in customer_sources:
            if source_id not in current:
                raise ValueError(
                    f"Customer grants require a current source: {source_id}."
                )
        pins = _release_pins(release)
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        with db:
            for source_id, versions in pins.items():
                for version, digest in versions.items():
                    title, sections = _guide(release_file, source_id, version, digest)
                    db.execute(
                        "INSERT INTO documents (source_id,title,created_at) VALUES (?,?,?) "
                        "ON CONFLICT(source_id) DO NOTHING",
                        (source_id, title, now()),
                    )
                    stored_title, stored_sections = stored_guide(db, source_id, version)
                    if stored_title != title:
                        raise ValueError(f"{source_id} has a different stored title.")
                    existing = db.execute(
                        "SELECT content_hash FROM document_versions "
                        "WHERE source_id=? AND source_version=?",
                        (source_id, version),
                    ).fetchone()
                    if existing is not None:
                        if (
                            existing["content_hash"] != digest
                            or stored_sections != sections
                        ):
                            raise ValueError(
                                f"{source_id} version {version} has different content."
                            )
                        continue
                    db.execute(
                        "INSERT INTO document_versions VALUES (?,?,?,?)",
                        (source_id, version, digest, now()),
                    )
                    db.executemany(
                        "INSERT INTO document_sections VALUES (?,?,?,?,?)",
                        (
                            (source_id, version, section_id, heading, text)
                            for section_id, (heading, text) in sections.items()
                        ),
                    )
            db.executemany(
                """
                INSERT INTO document_role_grants (source_id, role)
                VALUES (?, 'customer')
                ON CONFLICT(source_id, role) DO NOTHING
                """,
                ((source_id,) for source_id in customer_sources),
            )
    except (OSError, ValueError, sqlite3.Error) as error:
        raise click.ClickException(str(error)) from None
    click.echo("Citation release guides imported.")


def init_app(app):
    app.cli.add_command(import_citation_release)
    path = os.environ.get("DESKGUIDE_CITATION_RELEASE") or os.environ.get(
        "CITATION_RELEASE"
    )
    if path and app.config["CITATION_RELEASE"] is None:
        app.extensions.pop("citation_release_content", None)
        try:
            release = _read_release(Path(path))
            guides = _verified_guides(Path(path), release)
            app.extensions["citation_release_content"] = guides
            app.config["CITATION_RELEASE"] = release
        except (OSError, ValueError):
            # Keep the application available while source lookup fails closed.
            app.config["CITATION_RELEASE"] = path
