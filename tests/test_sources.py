"""Exercise C2b with fictional source data and real Flask sessions."""

import hashlib
import json
import sqlite3
from uuid import UUID

import pytest
from conftest import PASSWORD, write_json

from app import create_app
from app.db import get_db

URL = "/v1/sources/DOC-003/sections/s2"


def test_exact_and_default_citations_return_only_approved_content(
    client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200
    for suffix, version in (("?version=3", 3), ("", 3), ("?version=2", 2)):
        response = client.get(URL + suffix)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        body = response.json
        assert body.pop("correlation_id") == response.headers["X-Correlation-ID"]
        UUID(response.headers["X-Correlation-ID"])
        assert body == {
            "ref": {
                "source_id": "DOC-003",
                "section_id": "s2",
                "source_version": str(version),
            },
            "document_title": "VPN Setup Guide",
            "section_title": "Installing the client",
            "text": f"Text v{version}",
            "contract_version": "0.3.3",
        }


def test_missing_unreleased_retired_and_revoked_sources_share_a_404(
    app, client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200

    def error_at(url):
        response = client.get(url)
        assert response.status_code == 404
        error = response.json["error"]
        error.pop("correlation_id")
        return error

    missing = error_at(URL.replace("DOC-003", "DOC-999"))
    assert missing["code"] == "NOT_FOUND"
    # Version 1 is excluded and the newer version 4 is still a draft.
    for suffix in ("?version=1", "?version=4", "?version=999"):
        assert error_at(URL + suffix) == missing
    assert error_at(URL.replace("s2", "s9") + "?version=3") == missing

    with app.app_context(), get_db() as db:
        db.execute("UPDATE documents SET state = 'retired' WHERE source_id = 'DOC-003'")
    assert error_at(URL + "?version=2") == missing

    with app.app_context(), get_db() as db:
        db.execute("UPDATE documents SET state = 'active' WHERE source_id = 'DOC-003'")
        db.execute("DELETE FROM document_role_grants WHERE source_id = 'DOC-003'")
    assert error_at(URL + "?version=3") == missing
    assert error_at(URL + "?version=2") == missing

    with app.app_context(), get_db() as db:
        db.execute("INSERT INTO document_role_grants VALUES ('DOC-003', 'customer')")
        db.execute("DELETE FROM document_sections WHERE source_version = 3")
    assert error_at(URL + "?version=3") == missing
    assert client.get(URL + "?version=2").status_code == 200


def test_session_and_current_role_control_access(
    app, client, sign_in, released_sources
):
    assert client.get(URL).status_code == 401
    assert sign_in(client, "agent-one").status_code == 200
    assert client.get(URL + "?version=3&role=customer").status_code == 404
    with app.app_context(), get_db() as db:
        db.execute("INSERT INTO document_role_grants VALUES ('DOC-003', 'agent')")
    assert client.get(URL).status_code == 200


def test_database_rows_without_release_selection_are_inaccessible(
    app, client, sign_in, released_sources
):
    app.config["CITATION_RELEASE"] = None
    assert sign_in(client).status_code == 200
    assert client.get(URL).status_code == 404
    assert client.get(URL + "?version=3").status_code == 404


def test_customer_grants_narrow_role_access(app, client, sign_in, released_sources):
    other = app.test_client()
    assert sign_in(client).status_code == 200
    assert sign_in(other, "customer-two").status_code == 200
    with app.app_context(), get_db() as db:
        db.execute("INSERT INTO document_customer_grants VALUES ('DOC-003', 'c1')")
    assert client.get(URL + "?version=2").status_code == 200
    assert other.get(URL + "?version=2&customer_id=c1").status_code == 404


@pytest.mark.parametrize("invalid", [[], "2"])
def test_bad_release_configuration_returns_503(
    app, client, sign_in, released_sources, invalid
):
    assert sign_in(client).status_code == 200
    release = app.config["CITATION_RELEASE"]
    app.config["CITATION_RELEASE"] = (
        invalid
        if isinstance(invalid, list)
        else {**release, "historical": {"DOC-003": invalid}}
    )
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


def test_mismatched_content_hash_is_never_served(
    app, client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200
    with app.app_context(), get_db() as db:
        db.execute(
            "UPDATE document_versions SET content_hash = 'different' WHERE source_version = 3"
        )
    assert client.get(URL + "?version=3").status_code == 503


def test_retired_citations_use_explicit_cutoff(
    app, client, sign_in, clock, released_sources
):
    assert sign_in(client).status_code == 200
    app.config["CITATION_RELEASE"]["retired_until"] = {"DOC-003": clock[0] + 60}
    with app.app_context(), get_db() as db:
        db.execute("UPDATE documents SET state = 'retired'")
    assert client.get(URL).status_code == 404
    assert client.get(URL + "?version=3").status_code == 200
    clock[0] += 60
    assert client.get(URL + "?version=3").status_code == 404


def test_normal_startup_imports_and_opens_pinned_guide(tmp_path, monkeypatch, sign_in):
    def write_json(name, value):
        content = json.dumps(value).encode()
        (tmp_path / name).write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    manifest = {"review_status": "approved", "runtime_enabled": True}
    manifest_hash = write_json("evidence_manifest.json", manifest)
    guide = {
        "source_id": "DOC-003",
        "source_version": "3",
        "title": "VPN Setup Guide",
        "classification": "synthetic",
        "review_status": "pending_independent_review",
        "sections": [
            {"section_id": "s2", "title": "Install", "text": "Select Campus."}
        ],
    }
    guide_hash = write_json("DOC-003.v3.json", guide)
    release_path = tmp_path / "release.json"

    def write_release(digest):
        write_json(
            "release.json",
            {
                "manifest_sha256": manifest_hash,
                "current": {"DOC-003": {"version": "3", "sha256": digest}},
            },
        )

    write_release(guide_hash)
    monkeypatch.setenv("DESKGUIDE_INSTANCE_PATH", str(tmp_path / "instance"))
    monkeypatch.setenv("DESKGUIDE_LOCAL_HTTP", "1")
    monkeypatch.setenv("DESKGUIDE_CITATION_RELEASE", str(release_path))
    app = create_app()
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["seed-demo", "--password", PASSWORD]).exit_code == 0

    def import_guides(*options):
        return runner.invoke(
            args=["import-citation-release", str(release_path), *options]
        )

    rejected = import_guides()
    assert rejected.exit_code == 1
    assert "approved fictional data" in rejected.output
    guide["review_status"] = "approved"
    guide_hash = write_json("DOC-003.v3.json", guide)
    assert "Hash does not match" in import_guides().output
    write_release(guide_hash)
    assert import_guides().exit_code == 0
    app = create_app()
    client = app.test_client()
    assert sign_in(client, "customer-demo").status_code == 200
    assert client.get(URL + "?version=3").status_code == 404
    bad_grant = import_guides("--grant-customer", "DOC-999")
    assert bad_grant.exit_code == 1
    assert "Customer grants require a current source" in bad_grant.output
    assert client.get(URL + "?version=3").status_code == 404
    assert import_guides("--grant-customer", "DOC-003").exit_code == 0
    response = client.get(URL + "?version=3")
    assert response.status_code == 200
    assert response.json["text"] == "Select Campus."

    with app.app_context(), get_db() as db:
        db.execute("DELETE FROM document_role_grants")
    assert import_guides().exit_code == 0
    assert client.get(URL + "?version=3").status_code == 404

    write_json("evidence_manifest.json", {**manifest, "runtime_enabled": False})
    assert "Hash does not match" in import_guides().output


def test_unavailable_source_store_returns_dependency_error(
    client, sign_in, released_sources, monkeypatch
):
    def unavailable():
        raise sqlite3.OperationalError("test source store unavailable")

    assert sign_in(client).status_code == 200
    monkeypatch.setattr("app.sources.get_db", unavailable)
    response = client.get(URL + "?version=3")
    assert response.status_code == 503
    assert response.json["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


@pytest.mark.parametrize(
    "url",
    [
        URL.replace("DOC-003", "DOC-3"),
        URL.replace("s2", "s123"),
        URL + "?version=",
        URL + "?version=0",
        URL + "?version=-1",
        URL + "?version=3&version=4",
        URL + "?version=9223372036854775808",
    ],
)
def test_malformed_citation_returns_validation_error(client, sign_in, url):
    assert sign_in(client).status_code == 200
    response = client.get(url)
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_FAILED"


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE document_sections SET content='Unreviewed text' WHERE source_version=?",
        "UPDATE document_sections SET title='Unreviewed heading' WHERE source_version=?",
        "UPDATE document_sections SET section_id='s9' WHERE source_version=? AND section_id='s2'",
        "INSERT INTO document_sections VALUES ('DOC-003', ?, 's9', 'Extra', 'Unreviewed')",
    ],
)
def test_section_drift_with_unchanged_hash_is_never_served(
    app, client, sign_in, released_sources, version, mutation
):
    assert sign_in(client).status_code == 200
    with app.app_context(), get_db() as db:
        before = db.execute(
            "SELECT content_hash FROM document_versions WHERE source_version=?",
            (version,),
        ).fetchone()[0]
        db.execute(mutation, (version,))
        assert (
            db.execute(
                "SELECT content_hash FROM document_versions WHERE source_version=?",
                (version,),
            ).fetchone()[0]
            == before
        )
    section_id = "s9" if "section_id=" in mutation else "s2"
    response = client.get(URL.replace("s2", section_id) + f"?version={version}")
    assert response.status_code == 503
    assert "Unreviewed" not in response.get_data(as_text=True)
    result = app.test_cli_runner().invoke(
        args=["import-citation-release", str(released_sources)]
    )
    assert result.exit_code == 1
    assert "different content" in result.output


def test_document_title_drift_is_not_served_or_accepted_on_reimport(
    app, client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200
    with app.app_context(), get_db() as db:
        db.execute("UPDATE documents SET title='Unreviewed title'")
    assert client.get(URL).status_code == 503
    result = app.test_cli_runner().invoke(
        args=["import-citation-release", str(released_sources)]
    )
    assert result.exit_code == 1
    assert "different stored title" in result.output


def test_deleted_section_drift_rejects_reimport(app, released_sources):
    with app.app_context(), get_db() as db:
        db.execute("DELETE FROM document_sections WHERE source_version=3")
    result = app.test_cli_runner().invoke(
        args=["import-citation-release", str(released_sources)]
    )
    assert result.exit_code == 1
    assert "different content" in result.output


def test_release_without_verified_file_content_fails_closed(
    app, client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200
    del app.extensions["citation_release_content"]
    assert client.get(URL).status_code == 503


def test_changed_guide_file_cannot_bless_database_drift_after_restart(
    app, client, sign_in, released_sources
):
    assert sign_in(client).status_code == 200
    path = released_sources.with_name("DOC-003.v3.json")
    guide = json.loads(path.read_bytes())
    guide["sections"][0]["text"] = "Unreviewed text"
    write_json(path, guide)
    with app.app_context(), get_db() as db:
        db.execute(
            "UPDATE document_sections SET content='Unreviewed text' WHERE source_version=3"
        )
    # The existing worker retains the approved snapshot; the next worker rejects the file hash.
    assert client.get(URL).status_code == 503
    restarted = create_app({**app.config, "CITATION_RELEASE": None})
    assert "citation_release_content" not in restarted.extensions
    restarted_client = restarted.test_client()
    assert sign_in(restarted_client).status_code == 200
    assert restarted_client.get(URL).status_code == 503


def test_import_drift_rolls_back_new_source_and_does_not_restore_grants(
    app, released_sources
):
    path = released_sources.with_name("DOC-004.v1.json")
    digest = write_json(
        path,
        {
            "source_id": "DOC-004",
            "source_version": "1",
            "title": "Another Guide",
            "classification": "synthetic",
            "review_status": "approved",
            "sections": [{"section_id": "s1", "title": "Start", "text": "Reviewed."}],
        },
    )
    release = json.loads(released_sources.read_bytes())
    release["current"] = {
        "DOC-004": {"version": "1", "sha256": digest},
        **release["current"],
    }
    write_json(released_sources, release)
    with app.app_context(), get_db() as db:
        db.execute(
            "UPDATE document_sections SET content='Drift' WHERE source_version=2"
        )
        db.execute("DELETE FROM document_role_grants")
    result = app.test_cli_runner().invoke(
        args=[
            "import-citation-release",
            str(released_sources),
            "--grant-customer",
            "DOC-004",
        ]
    )
    assert result.exit_code == 1
    assert "different content" in result.output
    with app.app_context(), get_db() as db:
        assert (
            db.execute("SELECT 1 FROM documents WHERE source_id='DOC-004'").fetchone()
            is None
        )
        assert db.execute("SELECT 1 FROM document_role_grants").fetchone() is None


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE document_sections SET content='Drift' WHERE source_version=3 AND section_id='s1'",
        "DELETE FROM document_sections WHERE source_version=3 AND section_id='s1'",
    ],
)
def test_unchanged_section_is_withheld_when_a_sibling_drifts(
    app, client, sign_in, released_sources, mutation
):
    assert sign_in(client).status_code == 200
    with app.app_context(), get_db() as db:
        db.execute(mutation)
        assert (
            db.execute(
                "SELECT content FROM document_sections WHERE source_version=3 AND section_id='s2'"
            ).fetchone()[0]
            == "Text v3"
        )
    assert client.get(URL).status_code == 503
