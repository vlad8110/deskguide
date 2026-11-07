# C4 support-request backend

The customer-only C4 endpoints use the existing session, server-derived customer ownership and CSRF protection. Agents and document administrators cannot call these customer endpoints. No provider or customer-directory lookup is needed to save support.

## Endpoint flow

| Endpoint | Behavior |
| --- | --- |
| `POST /v1/escalations/submission-ids` | Accepts `{"operation":"escalation"}`. Registers an unused UUID for 30 minutes; creates no support request. |
| `POST /v1/escalations` | Requires `submission_id`, `reason`, `content` and boolean `consent_to_share: true`; optional `inquiry_id` and `note`. Atomically saves the request, receipt and completed registration. |
| `GET /v1/escalations/{submission_id}` | Returns owned registration/receipt status for escalation or reply IDs, including `saved`, request state and expiry. It does not return support content. |
| `POST /v1/escalations/{request_id}/reply-ids` | Accepts `{"operation":"reply"}` for an owned request in `waiting_for_customer`. Binds the new ID to that request. |
| `POST /v1/escalations/{request_id}/replies` | Requires `submission_id`, `message` and positive integer `expected_version`. Saves one reply and moves `waiting_for_customer` to `in_review`, retains the assigned agent and increments the version atomically. |

Every POST carries `X-CSRF-Token`. Responses include `contract_version: "0.3.3"` and a server-generated correlation ID. IDs are canonical lowercase UUID v4 strings. Request bodies reject unrecognized fields, including attempted customer/role overrides.

```json
{
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "reason": "insufficient_evidence",
  "content": "The Campus VPN profile is missing after installation.",
  "note": "Tried the documented steps.",
  "consent_to_share": true
}
```

Content is 1–1,000 characters; optional notes are at most 2,000. Reply messages are 1–2,000 characters. Text is normalized to Unicode NFC and trimmed; line breaks and tabs are allowed, other control/surrogate characters are rejected. The canonical text is what is stored and compared on retries. No unrelated inquiry text or history is copied. If provided, an inquiry must be owned and unexpired on the first save.

## Confirmation, replay and failure

The browser owns preview/edit/cancel. Registration alone saves only an intent. The confirmation POST must contain the text the customer reviewed and explicit consent. Cancelling requires no request: leave the ID unused to expire. The backend does not create server-side draft content or automatically submit fallback requests.

New saves return 201 only after commit, with a request ID and “Your request has been saved.” The acknowledgement promises neither an agent response nor a response time. Same ID and canonical payload returns 200 with the original result identity; changed payload returns 409. Replays report the request's current state (and current version for replies), without changing it. A completed reply replay remains valid after resolution but never reopens the request. A new late reply or stale version returns 409.

Receipts retain a random per-receipt salt and a SHA-256 comparison value covering customer scope, operation, parent and canonical payload; they contain no second support-text copy. This is a salted equality check, not encryption. It is independent of ephemeral application/session secrets, so same-ID recovery works across application restarts/instances sharing the database. Legacy fingerprints without this format fail closed rather than creating a new request.

Unknown, purged, foreign, wrong-operation and wrong-parent IDs return the same 404. Known expired unused IDs return 410. Completed receipts are checked before unused-ID expiry and admission limits. A known rolled-back write failure returns 503 `DEPENDENCY_UNAVAILABLE`; a failed commit acknowledgement returns 503 `SAVE_OUTCOME_UNCERTAIN`. Preserve the original ID and payload, check C4c or replay it; do not automatically get a replacement ID. Storage errors are logged only as a safe category and correlation ID.

SQLite write transactions enforce the three-ID cap atomically across escalation and reply registrations. Expired IDs do not consume a slot, and existing IDs are never evicted. New escalations are limited to five saved requests per customer per hour. Support admission is independent of C1/AI. `SUPPORT_MAX_OPEN_REQUESTS` defaults to 100 as a configurable local prototype bound, pending team sizing; it is not a measured production target. A full queue returns 503 `SERVICE_BUSY` for new requests/registrations; status, completed replays and replies to existing requests remain available.

## Database upgrade and retention

Migration [002_support_details.sql](../app/migrations/002_support_details.sql) adds nullable note/inquiry fields and a reply result reference. Version-1 bootstrap SQL remains unchanged. Existing databases require an explicit upgrade before using C4:

```sh
.venv/bin/python -m flask --app app migrate-db
```

Use the established local profile when starting Flask locally. Back up an existing database first. The migration is tested against a temporary version-1 database; project development does not automatically migrate the working database.

Open requests and their receipts are retained. Resolved requests become inaccessible through C4 after 30 days. `cleanup-support` atomically purges expired resolved requests, replies and receipts, then expired unused registrations. Inquiry deletion sets the optional support inquiry reference to null without deleting support. Schedule cleanup daily in a deployment; no scheduler or backup-deletion automation is installed by this change. The command does not delete open requests or their completed receipts.

## Review and remaining work

Hanlin connects preview/edit/cancel/confirm, same-ID retry/status and current-version reply UI. C5's agent queue, claim/state endpoints and customer detail view remain separate work; tests place requests into agent states directly. Production queue sizing, load/service-level measurement, backup restoration/deletion and independent peer review remain pending. No notification email, attachments, live chat or automatic reopening is implemented.

Run `.venv/bin/python -m pytest -q tests/test_support.py tests/test_migrations.py`. Tests exercise actual C4 routes with isolated fictional SQLite data, concurrent registration/submission/replies, replica recovery and injected write/commit failures.
