# C1 inquiry coordinator

`POST /v1/inquiries` accepts a customer question using the existing cookie session and `X-CSRF-Token`. Agents and document administrators cannot use this customer route. Customer scope comes from the server session; supplied role/customer fields do not grant access.

```json
{"requested_operation":"ask_question","question":"How do I set up the Campus VPN profile?"}
```

The response uses contract version `0.3.3`: `inquiry_id`, nullable `answer_id`, `status`, `route`, nullable `answer_origin` and `answer`, `sources`, nullable `clarification_prompt`, `escalation_offered`, nullable `suggested_reason`, `configuration_version` and `correlation_id`.

## Service integration

Register an implementation of [InquiryServices](../app/inquiry_types.py) at `app.extensions["inquiry_services"]`. There is no default provider or fictional answer service in the product application. Without configured services, the endpoint returns `temporarily_unavailable` with `service_unavailable`, null answer fields and empty sources.

The Flask entry point can pass the adapter constructor as
`create_app(inquiry_services_factory=build_inquiry_services)`. The constructor
receives the Flask app after its reviewed citation release has loaded. Use
`app.config["CITATION_RELEASE"]` for version pins,
`app.extensions["citation_release_manifest"]` for the verified manifest, and
`app.extensions["citation_release_content"]` for the verified guide contents.
Retrieval must apply current grants and the active pins. Citation lookup
continues to check current access on every open. Flask calls the constructor
only when the release contains verified guide content.

| Order | Internal method | Responsibility |
| --- | --- | --- |
| 1 | `retrieve(ctx, question, top_k=5, deadline_ms=...)` | Collins: enforce source access and approved-version selection; return permitted passages with their titles. |
| 2 | `prepare_evidence(ctx, inquiry_id, question, retrieved, deadline_ms=...)` | Collins: use the independently reviewed manifest; return ready with an immutable expectation, insufficient evidence, or unavailable checking. |
| 3 | `check_outbound(ctx, question, retrieved, deadline_ms=...)` | Collins/Vlad: approve both the question and every outgoing passage under the configured data policy; deny unknown or restricted content. |
| 4 | `generate(request)` | Collins: accept only question, permitted passage fields, timeout, configuration version and correlation ID. No identity, session or evidence expectation. |
| 5 | `validate(ctx, inquiry_id, candidate, retrieved, expectation, deadline_ms=...)` | Collins: recheck exact source resolution/current permission, active manifest/policy and answer support; return pass with all checked references. |

The coordinator checks expectation ownership, required excerpt ranges and text, cited-reference membership/coverage, and normalized equality to the preselected answer. Preparation must finish before generation. The original expectation is retained for the same inquiry. Missing checks, invalid output and dependency failures suppress the answer. Nothing retries generation or automatically creates support records.

`GenerationPassage` omits source display titles; those are used only to format the returned citation.

## C2b citation lookup

`GET /v1/sources/DOC-003/sections/s2?version=3` returns `ref`, `document_title`, `section_title`, `text`, `correlation_id` and `contract_version` to a signed-in user with a current role grant. Omitting `version` uses the active pin. Explicit links resolve only the requested approved version. If a document has customer-specific grants, a customer also needs an individual grant. For a retired document, only explicit approved links can open until its configured cutoff. Missing, withdrawn, expired and inaccessible sources return the same 404. Responses use `Cache-Control: no-store`.

Put the release file next to `evidence_manifest.json` and the pinned guide files, such as `DOC-003.v3.json`. The evidence manifest and each guide must be marked `"review_status": "approved"`, the manifest must have `"runtime_enabled": true`, and the guides must have `"classification": "synthetic"`. Use the hashes of the exact reviewed file bytes, for example with `shasum -a 256 evidence_manifest.json DOC-003.v3.json`.

```json
{
  "manifest_sha256": "<manifest SHA-256>",
  "current": {"DOC-003": {"version": "3", "sha256": "<guide SHA-256>"}},
  "historical": {},
  "retired_until": {}
}
```

`historical` maps a source ID to a list of eligible older pins with the same version and hash fields. Omit withdrawn versions. `retired_until` optionally maps a retired source ID to an explicit UTC Unix cutoff in seconds. With no cutoff, retirement closes citation access immediately.

After initializing the database, import the reviewed guides and point normal startup at the release file.

```bash
.venv/bin/python -m flask --app app import-citation-release /path/to/release.json
DESKGUIDE_CITATION_RELEASE=/path/to/release.json .venv/bin/python -m flask --app app run
```

Import does not grant access by default and preserves existing grants and retirement state. For a current source that is approved for all customers, pass `--grant-customer DOC-003` to `import-citation-release`. Repeat the option for each source that should receive this grant. A customer role grant with no customer-specific rows grants access to the customer role. To close access when removing the final individual grant, remove the role grant in the same transaction. An unset release serves no sources. At startup, the app verifies the pinned manifest and every guide file and keeps an immutable in-memory snapshot of their reviewed titles and sections, outside the database. Lookup checks the stored hash, document title and complete version section set against that snapshot before returning content. Invalid configuration, missing verified content or detected drift in a visible version returns 503. A missing requested section retains the generic 404 used for unavailable citations; changing stored text without changing its metadata hash cannot bless it as reviewed. A manually supplied `CITATION_RELEASE` mapping alone is insufficient: normal startup must load the verified release files.

Routine reimport compares existing titles, section IDs, headings and text with the verified guide and fails atomically on drift rather than silently accepting or overwriting it. It preserves existing grants and revocations. C8 updates must create a new version and obtain a new reviewed release pin, not overwrite approved rows. The current schema shares one document title across versions, so all pinned versions of one source must retain the same title. Restart workers after an approved release change; they retain their verified snapshots for their lifetime. These checks protect against source-row drift, not an attacker who can replace application configuration or code. Run `.venv/bin/python -m pytest -q tests/test_sources.py` to test startup, import and the route with fictional data in a temporary database.

## Admission, time and storage

SQLite transactions record admission before dependency work, with one active inquiry per customer, five inquiries per rolling minute and a configurable application-wide cap (`INQUIRY_MAX_ACTIVE`, default 5). A second active inquiry returns 429; aggregate saturation returns 503 `SERVICE_BUSY`, both with `Retry-After`. There is no application work queue. These are local prototype inquiry limits, not provider quota/token enforcement or measured production capacity. Abandoned processing markers stop consuming admission after 20 seconds.

Dependencies receive a remaining-time budget: retrieval at most 2 seconds, generation at most 12 seconds, and a one-second fallback reserve inside the 20-second inquiry budget. The coordinator discards returned results that exceed a stage budget; a result beyond the overall deadline yields 504. **Adapters must implement cancellable or bounded I/O using the supplied timeout.** This synchronous coordinator cannot interrupt a dependency that ignores its timeout or protect against an indefinitely blocked call. Do not connect an unbounded adapter. Timeout tests use a controlled clock; they are not live latency measurements.

Only inquiry ID, trusted customer ownership, route, outcome, answer ID, configuration version and creation/expiry times are persisted. No question, answer or passage text is saved or logged. Inquiry metadata expires after 30 days by timestamp. Use `flask --app app cleanup-inquiries` to purge expired metadata and its linked feedback. Source-reference persistence and automatic scheduling remain separate. C1 needs no schema change; the separate [C4 backend](support-backend.md) adds migration 2.

## Remaining connections

- Collins and Vlad: connect the same reviewed release selection to retrieval and citation lookup. Collins owns C10 validation and outbound policy implementation before connecting a real generation adapter. Account/model/data controls, token/request limits and the shared circuit breaker remain separate provider work.
- Hanlin: connect question/result states and source views, add the agreed notice, and preserve questions on fallback. This backend returns a support offer; the existing browser shell does not yet display it.
- Vlad: connect C7 for explicit `check_account_status`; it currently returns a controlled service-unavailable escalation offer without retrieval/generation. Conversation IDs are rejected unless null because conversation ownership is not implemented. Explicit human-request recognition, clarification prompts and feedback remain separate workflows. [C4](support-backend.md) now provides the separately confirmed support backend; C1 never calls its save route automatically.
- David: review the integration types and endpoint cases, independently verify evidence fixtures, and extend tests when actual adapters/source routes arrive. Synthetic tests do not establish live-provider or production capacity.

Run `.venv/bin/python -m pytest -q tests/test_inquiries.py` for the endpoint regressions. Test substitutes exist only in the tests and are never installed by application startup.
