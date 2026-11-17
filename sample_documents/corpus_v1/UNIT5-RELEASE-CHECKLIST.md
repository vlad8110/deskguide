# Unit 5 — exact three-guide Cohere alpha release candidate

This directory contains **proposed**, SHA-256-pinned synthetic material for an
independent release decision. Opening the PR or committing the `approved`
metadata does **not** constitute release authorization, production permission
validation, or proof of a live Cohere test. Do not merge/deploy until the
independent reviewer and release owner record acceptance of this exact commit.

## Frozen candidate

`release.json` pins **only** `DOC-001 v1`, `DOC-002 v1`, `DOC-003 v3`,
and the approved, enabled `evidence_manifest.json`. There are no historical
pins or retirement exceptions. The guide section text, titles, evidence
aliases, excerpts, and approved answers are unchanged from the independently
reviewed draft; only the `review_status` metadata in each guide, plus
`review_status` and `runtime_enabled` in the manifest, have changed.
Those metadata changes produce **new SHA-256 file hashes**, recorded in
`release.json`.

Verify exact file bytes and relationships:

```sh
python -m pytest -q tests/test_alpha_release.py tests/test_sources.py tests/test_cohere_services.py
```

The test checks the release pins, SHA-256 hashes, exact versions, source
classification and approval, complete excerpt offsets, unique exact aliases,
the VPN citation (`DOC-003/s2/v3`) and the printer-driver fallback fixture
(with zero *expected* Cohere calls). Tests alone do not authorize deployment.

## Proposed customer-access policy and activation procedure

Apply to a **fresh, fictional alpha database** or audit a persistent one
before import. The approved policy is role-wide **customer** access to exactly
these three current synthetic sources. No agent/admin role grant and no
per-customer restriction is proposed for this alpha. Unknown sources,
historical versions and missing role grants must remain inaccessible.
A source's customer-role grant should be removed in the same transaction if
the final individual customer grant is revoked; otherwise role-wide access
could become broader than intended.

After the exact release and policy have received independent sign-off, and
after the Cohere integration PR has been merged and its code deployed:

```sh
python -m flask --app app init-db
python -m flask --app app import-citation-release sample_documents/corpus_v1/release.json \
    --grant-customer DOC-001 --grant-customer DOC-002 --grant-customer DOC-003
```

**Important:** Import is additive; it preserves pre-existing grants and does
not revoke older ones. On any reused DB, a release owner must verify (or
transactionally remove) unauthorized prior rows. At minimum audit these tables:

```sql
SELECT source_id, role FROM document_role_grants ORDER BY source_id, role;
SELECT source_id, customer_id FROM document_customer_grants ORDER BY source_id, customer_id;
SELECT source_id, state FROM documents ORDER BY source_id;
SELECT source_id, source_version, content_hash FROM document_versions
ORDER BY source_id, source_version;
```

Before live acceptance, confirm (1) the selected three sources have
`customer` grants, (2) no unexpected grants exist, (3) there are no
`document_customer_grants` limiting the intended role-wide access,
(4) all three approved documents are active, (5) stored hashes match
`release.json`, and (6) unknown/unapproved/retired sources and unauthorized
customers are denied. Preserve evidence without copying personal records.

Once separately authorized, set `DESKGUIDE_CITATION_RELEASE` to the
absolute path to `release.json` and configure `DESKGUIDE_AI_PROVIDER=cohere`
and the **server-only** `COHERE_API_KEY` under your secrets manager.
Do not commit keys or real employee data.

## Live acceptance, explicitly not yet passed

On the exact deployed commit and documented Cohere account/model:
- With a signed-in authorized customer, ask
  `How do I set up the Campus VPN profile?`. Confirm the answer is supported
  by `DOC-003`, section `s2`, version `3`, and that opening the citation
  resolves the approved section.
- Ask `Which printer driver should I install?`. Confirm support is offered
  and **the provider call count is zero** using trusted transport/request
  evidence rather than merely the user-interface response.
- Check denied/retired/drifted source behavior, current grants before
  outbound transmission, response validation, provider errors, redacted
  logs, and the customer-to-agent support-request flow.

If the first release fails, **disable the AI provider and leave the support
request path available**; there is no prior approved release to roll back to.
Capture the deployed commit, hashes, grant audit, provider setup, test records,
owner/reviewer names and acceptance decision in Issue #4 and Issue #14.
