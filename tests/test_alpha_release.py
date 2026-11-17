"""Verify Unit 5's exact synthetic, approval-gated three-guide alpha release.

This is a static release/fixture check; it does not contact Cohere or inspect
the deployed database or prove runtime customer grants.
"""

import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "sample_documents" / "corpus_v1"
EXPECTED = {"DOC-001": "1", "DOC-002": "1", "DOC-003": "3"}
VPN_QUESTION = "How do I set up the Campus VPN profile?"
PRINTER_QUESTION = "Which printer driver should I install?"


def _read_pinned(name: str, expected_hash: str) -> dict:
    raw = (ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_hash, name
    return json.loads(raw)


def test_exact_unit5_three_guide_release_and_evidence():
    release = json.loads((ROOT / "release.json").read_bytes())
    assert set(release) == {"manifest_sha256", "current", "historical", "retired_until"}
    assert release["historical"] == {} and release["retired_until"] == {}
    assert set(release["current"]) == set(EXPECTED)

    manifest = _read_pinned("evidence_manifest.json", release["manifest_sha256"])
    assert manifest["review_status"] == "approved"
    assert manifest["runtime_enabled"] is True

    guides = {}
    for source_id, version in EXPECTED.items():
        pin = release["current"][source_id]
        assert set(pin) == {"version", "sha256"}
        assert str(pin["version"]) == version
        guide = _read_pinned(f"{source_id}.v{version}.json", pin["sha256"])
        assert guide["source_id"] == source_id
        assert str(guide["source_version"]) == version
        assert guide["classification"] == "synthetic"
        assert guide["review_status"] == "approved"
        ids = [s["section_id"] for s in guide["sections"]]
        assert len(ids) == len(set(ids))
        guides[source_id] = {
            section["section_id"]: section["text"] for section in guide["sections"]
        }

    aliases = set()
    vpn = None
    assert len(manifest["intents"]) == 8
    for intent in manifest["intents"]:
        for alias in intent["aliases"]:
            normalized = " ".join(unicodedata.normalize("NFC", alias).split())
            assert normalized not in aliases
            aliases.add(normalized)
            if normalized == VPN_QUESTION:
                vpn = intent
        for excerpt in intent["required_excerpts"]:
            ref = excerpt["ref"]
            assert str(ref["source_version"]) == EXPECTED[ref["source_id"]]
            content = unicodedata.normalize(
                "NFC", guides[ref["source_id"]][ref["section_id"]]
            )
            assert content[excerpt["start"] : excerpt["end"]] == excerpt["text"]
        assert intent["approved_answer"]

    assert len(aliases) == 8
    assert vpn is not None
    assert vpn["required_excerpts"][0]["ref"] == {
        "source_id": "DOC-003",
        "section_id": "s2",
        "source_version": "3",
    }
    assert PRINTER_QUESTION not in aliases

    evaluations = json.loads((ROOT / "evaluation_questions.json").read_bytes())
    assert len(evaluations["cases"]) == 20
    printer = next(c for c in evaluations["cases"] if c["question"] == PRINTER_QUESTION)
    assert printer["expected_preparation"] == "insufficient_evidence"
    assert printer["expected_generation_calls"] == 0
