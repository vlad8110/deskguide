# C5 agent support workflow

C5 exposes the unassigned queue and the signed-in agent's assigned requests. Customers and document administrators receive 403. Ownership comes from the server session; a browser cannot select another agent. All POST endpoints require `X-CSRF-Token`.

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/agent/escalations` | Lists unassigned queued requests and the caller's assigned requests. Optional `state`, `limit` (1–100, default 25) and signed `cursor`. |
| `GET /v1/agent/escalations/{request_id}` | Assigned agent only: request content/note, messages, state and version. Missing, unassigned, expired or another agent's detail returns 404. |
| `POST /v1/agent/escalations/{request_id}/claim` | No body. Atomically claims a queued request, sets the caller as owner, moves to `assigned`, increments version and records the event. A second claimant gets 409. |
| `POST /v1/agent/escalations/{request_id}/transition` | Requires `to_state` and integer `expected_version`, plus the conditional field below. Owner/state/version are checked atomically. |
| `GET /v1/escalations/requests/{request_id}` | Owning customer only: reviewed content/note, customer-visible messages and current state/version for C4 replies. No internal resolution notes or agent audit data. |

Queue summaries contain `request_id`, `state`, `content`, `reason`, `created_at`, `assigned_agent_id`, `customer_ref`, `account_status` and `version`; they omit notes and message history. `account_status` remains null because C7 is not connected. Listing and handling support do not depend on C7 or an AI provider. Queue rows come directly from committed support records; no broker is required.

Pagination orders by creation time and request ID, returning at most `limit` rows and `next_cursor`. A cursor is signed, tied to agent/filter and expires in 15 minutes. It cannot authorize a wider query; every page rechecks the caller's scope. Use a stable shared `SECRET_KEY` across deployed replicas; restarting the ephemeral local profile invalidates old cursors safely. Pagination is a live queue, not a frozen snapshot: new claims/releases can change later pages.

## Five states and owner actions

| From | To | Required action/text |
| --- | --- | --- |
| `queued` | `assigned` | Agent claims through the claim endpoint. |
| `assigned` | `in_review` | Assigned agent starts review. |
| `in_review` | `waiting_for_customer` | Owner supplies `message_to_customer` (1–2,000 characters). |
| `waiting_for_customer` | `in_review` | Owner resumes review, or a valid C4 customer reply moves it atomically and retains ownership. |
| `in_review` | `resolved` | Owner supplies `resolution_note` (1–2,000 characters). |
| Any of the three active assigned states | `queued` | Owner supplies `release_reason` (1–500 characters); ownership clears. |
| `resolved` | None | Terminal. No reopening or takeover. |

Release from review/waiting follows the working D12 direction and remains subject to team review. Missing required text gives 400. Unrelated conditional fields and identity fields are rejected. C5's reviewed examples distinguish known non-owner write attempts/second claims (409) from another agent's private detail lookup (404). Unknown/expired request IDs return 404. Stale versions and invalid state transitions give 409 without changing text, owner or state. Reload before deciding again; do not blindly resubmit a transition.

```json
{
  "to_state": "waiting_for_customer",
  "expected_version": 3,
  "message_to_customer": "Which fictional network are you using?"
}
```

Customer-visible questions and internal resolution notes are stored separately from the audit. Details combine them with C4 replies; request-version ordering preserves sequence when messages share a timestamp. Internal resolution notes are visible only to the currently assigned agent. Release-reason text is validated but not persisted; the audit records only that a reason was provided.

Every claim/transition, including the C4 customer-reply transition, records actor, role, operation, old/new state, resulting version, correlation ID and timestamp in the same transaction. No request, reply, release-reason or message text enters the audit. A failed audit/message write rolls back the state change. If a commit acknowledgement is lost, C5 returns a safe 503 asking the agent to reload; a transition is not automatically replayed. C4 retains its separate same-ID receipt recovery.

## Upgrade, retention and handoff

Migration `003_agent_workflow.sql` adds agent messages, content-free state events, reply ordering and queue indexes. Existing version-1/version-2 records are preserved; legacy replies have no invented event/version history. Back up an existing database, then run the established `migrate-db` command before starting this revision. The working database is not automatically upgraded by development.

Agent and customer detail/list routes hide resolved records after 30 days. `cleanup-support` cascades their agent messages/events when purging the request, along with the existing C4 cleanup. No scheduler or backup-deletion automation is installed here.

Hanlin connects the agent queue/detail/claim/transition controls and the customer detail/reply screen. David reviews role/privacy, concurrent claims and updates, C4/C5 races, rollback and retention. Browser views, notifications, production capacity, provider integration and final peer acceptance remain pending. The local tests use actual C4/C5 endpoints with fictional SQLite data, not a live production workload.

Run `.venv/bin/python -m pytest -q tests/test_agent_support.py tests/test_support.py tests/test_migrations.py` for the focused endpoint/migration checks.
