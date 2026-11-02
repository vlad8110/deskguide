# DeskGuide Interface Contracts (Draft 3, aligned to the Nov 1 architecture review and PR #17 feedback)

**Lead:** Hanlin | **Reviewers:** Collins (interfaces), David (verification) | **Architecture check:** Vlad
**Status:** Draft 3 for review. Revises Draft 2 to match Vlad's architecture review (Nov 1), the issue #12 follow-up (D05, D09, D11, D12, D17, D18) and Collins's review on PR #17. All limits are **proposed**, not team-approved. No implementation, provider access, or measured capacity is claimed. All examples are fictional.
**Workload basis (Vlad):** 10,000 concurrent customer sessions, 1 new inquiry per customer per minute on average, about 167 new inquiries per second (10,000 / 60 = 166.67). This is a planning assumption, not measured usage.

---

## 1. Alignment map

### 1.1 Components, contracts and names

| Vlad | Contract component (this document) | Collins's name | Contracts it owns or serves |
|---|---|---|---|
| M1 Browser interfaces | Browser UI (caller only; never authoritative) | Customer interface | Calls C1, C4, C5, C6, C8, C9b |
| M2 Application and access control | `InquiryService` + `AccessControl` | Inquiry coordinator | C1, C9 |
| M3 Knowledge and retrieval | `Retriever`, `DocumentService` | Retrieval/source service | C2, C8 |
| M4 AI provider adapter | `GenerationAdapter` | Generation adapter | C3 |
| M5 Answer and source validation | `AnswerValidator` | Output validator | C10 |
| M6 Escalation and agent workflow | `EscalationService`, `AgentQueueService` | Escalation service, Agent service | C4, C5 |
| M7 Customer-data adapter | `CustomerDirectoryAdapter` | Customer-data adapter | C7 |
| M8 Feedback and reviewed improvement | `FeedbackService` | Feedback/review service | C6 |
| M9 Persistence adapters | Storage interfaces owned by M3, M6, M8 (sessions, receipts and shared breaker state are also held through M9) | (not named) | Supports C2, C3, C4, C5, C6, C8, C9 |

Logical components do not imply separate deployed services. Vlad's proposed deployment is one modular Flask application replicated behind HTTPS ingress, with shared PostgreSQL state. Replicas therefore share sessions, escalation receipts and circuit-breaker state through M9, and no contract may rely on in-process memory for any of these.

### 1.2 Contract inventory

| ID | Interaction | Interface | Backlog / requirement |
|---|---|---|---|
| C1 | Customer inquiry and answer | `POST /v1/inquiries` | B10, R1 |
| C2 | Retrieval and source access | `retrieve()`, `GET /v1/sources/{source_id}/sections/{section_id}` | B07, R1 |
| C3 | AI generation adapter | `generate()` | B05, B10, B11 |
| C4 | Human escalation | C4a `POST /v1/escalations/submission-ids`, C4b `POST /v1/escalations`, C4c `GET /v1/escalations/{submission_id}`, C4d `POST /v1/escalations/{request_id}/replies` | B11, R2 |
| C5 | Agent review and update | `GET /v1/agent/escalations`, `.../{request_id}/claim`, `.../{request_id}/transition` | B13, R2 |
| C6 | Feedback and reviewed improvement | feedback and improvement-proposal endpoints | B13, B16, P04, R3 |
| C7 | Existing customer database | `get_customer_profile()` | P02, R5 |
| C8 | Document administration | `/v1/admin/documents` | B14 |
| C9 | Access context and session | `AccessContext` type (C9a); `GET /v1/session`, `POST /v1/session/logout` (C9b) | B09, all |
| C10 | Answer and source validation | `validate()` | B07, B10 |

Note: Draft 2 called the escalation status lookup C4b and the customer reply C4c. Draft 3 inserts the ID-registration step as C4a, so the sub-contracts are renumbered (see Section 6).

---

## 2. Shared conventions

**Roles (server-derived, never trusted from the browser):** `customer`, `agent`, `administrator`.
Administrator rights cover document administration (C8) only. They do **not** grant access to customer conversations, escalations, or raw feedback (C4, C5, C6 content).

**Enum style.** Enum values are lowercase snake_case, matching Collins's flows. Error codes are UPPER_SNAKE.

**Versioning.** `/v1/` path prefix. Responses include `contract_version` (currently `"0.3"` while drafting).

### 2.1 Authentication, session and CSRF (D18)

Vlad's architecture uses opaque server-side sessions in cookies. Draft 2's bearer-token header is removed.

| Item | Rule |
|---|---|
| Session credential | Opaque session identifier in a cookie with `Secure`, `HttpOnly`, `SameSite=Lax`. The browser never reads it. Session records live in shared storage (M9), not in one replica's memory. |
| Identity source | The server derives role and `customer_scope` from the session record. Nothing about identity is read from request bodies, query strings or headers. |
| CSRF | Every state-changing request (`POST`, `PUT`, `DELETE`) must carry `X-CSRF-Token` matching the token bound to the session. Mismatch or absence returns 403 `CSRF_FAILED`. `GET` requests never change state. |
| Expiry | Idle expiry V23 and absolute expiry V24 (both proposed). An expired or unknown session returns 401 `UNAUTHENTICATED`. The browser must start a new session; the server never silently extends a session past the absolute limit. |
| Logout | `POST /v1/session/logout` invalidates the current session record server-side. Scope is the current session only (proposed). Logout of all sessions is open (Section 7). |
| Provisioning | How identities and roles are created (identity provider, import, manual) is **not specified** in this draft. It is open for Vlad (Section 7). Contracts assume a valid session already carries `subject_id` and `role`. |

### 2.2 Headers

| Header | Rule |
|---|---|
| `Cookie` (session) | Required on all endpoints except the sign-in step, which is outside this draft |
| `X-CSRF-Token` | Required on all state-changing requests; value obtained from `GET /v1/session` |
| `X-Correlation-ID` | **Server-generated** and returned on every response. Any client-supplied value is ignored. |
| `Retry-After` | Seconds, sent on 429 and 503. Servers should add jitter to avoid synchronized retries. |

### 2.3 Identifiers

| ID | Meaning | Generated by |
|---|---|---|
| `correlation_id` | Trace one inquiry across components | Server |
| `inquiry_id`, `answer_id` | An inquiry and its candidate-turned-answer | Server |
| `submission_id` | One intentional customer escalation submission. **Issued and registered by the server** (C4a), bound to the customer and the operation. Reused only for retries of the same submission. | **Server** (Draft 2: browser) |
| `request_id` | The durably saved support request | Server |
| `source_id`, `section_id`, `source_version` | Exact evidence reference | Knowledge store |
| `configuration_version` | Prompt, retrieval and model configuration used | Server |

### 2.4 Common types

| Type | Definition |
|---|---|
| `Uuid` | UUID v4 string |
| `Timestamp` | ISO 8601 UTC |
| `SourceRef` | `{ source_id: "DOC-003", section_id: "s2", source_version: "3" }`. `source_id` matches `^DOC-[0-9]{3}$`; `section_id` matches `^s[0-9]{1,2}$`; `source_version` is a positive integer string. |
| `AnswerStatus` | `answered`, `clarification_requested`, `escalation_offered`, `temporarily_unavailable` |
| `Route` | `ai`, `account_status`, `human_requested`. Decided by `InquiryService` **before** admission (Vlad, step A2). Used to define the service-level denominator (2.7). |
| `EscalationReason` | `insufficient_evidence`, `human_requested`, `validation_failed`, `provider_failure`, `service_unavailable`, `action_required`. `service_unavailable` (new) covers retrieval or customer-data failure so that "insufficient evidence" stays distinct from "service unavailable". |
| `RequestState` | `queued`, `assigned`, `in_review`, `waiting_customer`, `resolved`. (Draft 2 spelled the fourth state `waiting_for_customer`; Draft 3 follows Vlad's `waiting_customer`.) |
| `RegistrationState` | `unused`, `completed`, `expired` |

### 2.5 Error envelope (all non-2xx)

```json
{
  "contract_version": "0.3",
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Your question must be between 1 and 1000 characters.",
    "retryable": false,
    "correlation_id": "6f1c2a9e-3b7d-4d0a-9c11-2f5e8a7b1d42",
    "details": [{"field": "question", "rule": "length_1_1000"}]
  }
}
```

`message` is safe and user-facing. It never contains stack traces, provider names, SQL, or credentials. `details` appears only for `VALIDATION_FAILED` and lists field names, not values.

| Code | HTTP | Retryable | Meaning |
|---|---|---|---|
| `VALIDATION_FAILED` | 400 | No | Malformed or out-of-range input |
| `UNAUTHENTICATED` | 401 | No | Missing, invalid or expired session |
| `FORBIDDEN` | 403 | No | Role or scope not permitted |
| `CSRF_FAILED` | 403 | No | State-changing request without a valid CSRF token |
| `NOT_FOUND` | 404 | No | Missing, or outside caller's scope (same response for both) |
| `CONFLICT` | 409 | No | Illegal transition, ownership/version conflict, or reused `submission_id`/reply version with different content |
| `FEEDBACK_WINDOW_CLOSED` | 409 | No | Feedback submitted after the acceptance window (V26) |
| `SUBMISSION_ID_EXPIRED` | 410 | No | A registered but unused `submission_id` passed its validity period. The customer must register a new one (C4a); the server never recreates it. |
| `RATE_LIMITED` | 429 | Yes | Per-customer limit reached |
| `INTERNAL_ERROR` | 500 | Yes | Unexpected failure, no details exposed |
| `SERVICE_BUSY` | 503 | Yes | Aggregate admission bound reached; includes `Retry-After` |
| `DEPENDENCY_UNAVAILABLE` | 503 | Yes | Storage or other required dependency down. For C4b this means **the save is known to have failed; nothing stored**. |
| `SAVE_OUTCOME_UNCERTAIN` | 503 | Yes | C4b only. The commit outcome is unknown ("confirmation unavailable"). The client must resolve it with the same `submission_id` (C4c or a same-content retry) and must not claim that nothing was saved. |
| `DEADLINE_EXCEEDED` | 504 | Yes | End-to-end deadline passed before any controlled outcome could be returned (see C1) |

### 2.6 Privacy and logging (all contracts)

Permitted log fields: `correlation_id`, normalized error category, duration, `configuration_version`, retry count. Not logged: question, answer, note, comment text, session identifiers, CSRF tokens, provider keys, raw provider errors. *Open (David):* whether `subject_id` may be logged for audit.

### 2.7 Service target and overload (D11, planning basis 167 inquiries/s)

**Proposed service level (Vlad, awaiting capacity evidence):** at least 95% of **eligible** inquiries receive a supported AI answer within 15 seconds.
- *Eligible* means a valid, authorized, in-scope inquiry with supporting evidence, assigned `route: ai` before admission.
- Busy responses, timeouts, invalid answers and unnecessary fallbacks count as **misses** and stay in the denominator.
- Explicit human requests (`route: human_requested`) and genuinely unsupported questions are reported separately.
- Applies a 20 s end-to-end deadline (V4) and a provider timeout of at most 12 s (V6).

C1 therefore returns `route` and the server records the outcome status so David can compute the ratio.

**Admission.**
- Per-customer limits plus an aggregate AI-generation concurrency limit (V15, open).
- **No AI waiting queue** (Vlad). If admission or dependency capacity is not available, return `SERVICE_BUSY` with `Retry-After` immediately and preserve the question in the browser. There is no queue-wait term in the deadline.
- Escalation (C4, C5) has its own bounded admission, independent of generation, so a human handoff stays available when AI is saturated.
- Illustration only: average in-flight inquiries = (10,000 / 60) x mean end-to-end seconds, for example 834 at 5 s, 1,667 at 10 s, 2,500 at 15 s (Vlad's table). These are not targets or measurements.
- Proposed simulated load scenarios for David (against controlled substitutes, not a live provider): 166.67/s steady; 333.33/s for two minutes; a separate burst of 10,000 arrivals in one second.

**Data ownership.** Each component owns its records and rules; others use its interface, not its tables.

| Owner | Records |
|---|---|
| `Retriever` / `DocumentService` (M3) | Documents, sections, versions |
| `EscalationService` / `AgentQueueService` (M6) | Support requests, registered submission IDs, completed receipts, states |
| `FeedbackService` (M8) | Feedback, improvement proposals, releases |
| `AccessControl` (M2) | Session records (stored through M9) |
| `GenerationAdapter` (M4) | Shared circuit-breaker state and trial lease (stored through M9) |
| `CustomerDirectoryAdapter` (M7) | No stored copy (read-through, optional short cache) |

---

## 3. Proposed values and decisions

Status key: **Proposed** = drafted here, needs team approval. **Open** = no value yet. **Closed (proposed)** = Draft 3 resolves it to match Vlad's or Collins's text, pending confirmation.

| # | Value | Proposed | Justification | Status |
|---|---|---|---|---|
| V1 | Question length | 1-1,000 chars | Support-question size; bounds AI input | Proposed |
| V2 | `top_k` | default 5, max 8 | Context vs tokens | Proposed |
| V3 | Passage text sent to AI | max 1,500 chars each | Bounds prompt size | Proposed |
| V4 | End-to-end inquiry deadline | 20 s (no queue-wait term) | Vlad's architecture review | Closed (proposed) |
| V5 | Retrieval timeout | 2 s | Index lookup | Proposed |
| V6 | Provider call timeout | min(12 s, remaining deadline) | Vlad: at most 12 s (Draft 2: 15 s) | Closed (proposed) |
| V7 | Customer DB timeout | 2 s | Keyed lookup | Proposed |
| V8 | Per-customer inquiry limit | 5 per minute | Normal chat use; 167/s across 10,000 sessions is about 1 per minute average | Proposed |
| V9 | Per-customer escalation submit limit | 5 per hour | Prevents queue flooding | Proposed |
| V10 | Escalation content / note length | 1-1,000 / 0-2,000 chars | Room for context | Proposed |
| V11 | Completed-receipt retention | Request lifetime plus 30 days after resolution | Vlad's walkthrough B5 (Draft 2: 24 h) | Closed (proposed); David to confirm privacy impact |
| V12 | Feedback comment length | 0-500 chars | Short comments | Proposed |
| V13 | Agent queue page size | default 25, max 100 | Small responses | Proposed |
| V14 | Peak factor over 167 inquiries/s | not set | Needs Vlad and David | **Open** |
| V15 | Aggregate generation concurrency limit | not set | Depends on V14 and provider quota (Collins) | **Open** |
| V16 | AI queue size and queue-wait limit | **none**: no AI waiting queue | Vlad: bounded admission, immediate `SERVICE_BUSY` | Closed (proposed) |
| V17 | Provider retry budget | 0 automatic generation retries | Vlad and Collins: no automatic retry, no second-provider failover | Closed (proposed); Collins to confirm |
| V18 | Circuit breaker | 3 qualifying failures within 60 s opens it; 30 s cooldown; then one global half-open trial protected by a 20 s lease per provider/model/credential scope. State shared through M9. | Vlad's M4 proposal. Counter, reset and write policy are Collins's. | Proposed; **Open** on counter/reset/write (Collins) |
| V19 | Evidence-sufficiency rule (pre-generation) and runtime evidence-support rule (C10) | not set | Collins defines the executable rules; C10 defines where they plug in | **Open** (Collins) |
| V20 | Tenant model (single or multi) | not set | Isolation boundary for scope and caches | **Open** (Vlad) |
| V21 | Retention for feedback and requests | not set | Privacy decision | **Open** (David) |
| V22 | Customer-data allowlist | `customer_id`, `account_status` only | Vlad: initial case is read-only account status, deterministic, no AI | Proposed. Which inquiries need it remains **Open**. |
| V23 | Session idle expiry | 30 min | Typical for a support chat; limits stolen-session window | Proposed (Hanlin; Vlad and David to confirm) |
| V24 | Session absolute expiry | 8 h | Bounds a session regardless of activity | Proposed |
| V25 | Unused `submission_id` validity | 30 min from registration; max 3 unused IDs outstanding per customer | Long enough to review and edit, short enough to bound stale IDs | Proposed; Vlad lists as pending |
| V26 | Feedback acceptance window | 7 days after the inquiry | Prevents stale, unattributable feedback. Hanlin's reading of "feedback expiry" (D05). | Proposed; Vlad to confirm the intended meaning |
| V27 | Service level | 95% of eligible inquiries answered within 15 s | Vlad (D11) | Proposed; awaits capacity evidence |
| V28 | Fallback reserve before the 20 s deadline | 1 s | Leaves time to return a controlled 200 instead of 504 | Proposed; Collins to confirm |
| V29 | Customer reply version window | One accepted reply per `waiting_customer` turn | Prevents duplicate replies (D12) | Proposed; David to review |

---

## 4. Contracts

### C9. Access context and session (defined first because every contract uses it)

**Owner:** `AccessControl` (M2).

**C9a. `AccessContext` (internal type).** Built server-side from the validated session record. Never accepted from the browser.

```
AccessContext {
  subject_id:     string        # authenticated user, required
  role:           Role          # customer | agent | administrator
  customer_scope: string|null   # customer_id for customers; null for agent/administrator
  tenant_id:      string|null   # null until V20 decided
  correlation_id: Uuid          # server-generated
  issued_at:      Timestamp
}
```

Every **internal business method that authorizes data access** takes an `AccessContext` as its first argument (`retrieve`, `validate`, `get_customer_profile`, and the service methods behind C1, C4-C8). **Exception, deliberately:** `GenerationAdapter.generate()` (C3) takes no `AccessContext`. `InquiryService` holds the context, performs every authorization check **before** calling the provider adapter, and passes only the permitted question, permitted passages, `deadline_ms`, `configuration_version` and `correlation_id`. Nothing from C9a (role, subject, customer scope, tenant, session) and no customer-database field ever reaches the provider (Collins's point 1, Vlad's M4 text).

| Condition | Result |
|---|---|
| Session missing, unknown, expired | 401 `UNAUTHENTICATED` |
| Role not allowed for the endpoint | 403 `FORBIDDEN` |
| State-changing request without valid CSRF token | 403 `CSRF_FAILED` |

**C9b. Session endpoints**

| Endpoint | Auth | Behavior |
|---|---|---|
| `GET /v1/session` | Any role | Returns `{ role, expires_at, idle_expires_at, csrf_token, correlation_id, contract_version }`. Never returns `customer_scope` values or the session identifier. |
| `POST /v1/session/logout` | Any role, CSRF required | Invalidates the current session record. Returns 204. A repeated call with an already-invalid session returns 401. |

**Tests:** forged `customer_id` or `role` in a body is ignored; customer session calling an agent endpoint returns 403; administrator session calling C4/C5/C6 content endpoints returns 403; expired (idle and absolute) session returns 401; `POST` without CSRF token returns 403 `CSRF_FAILED`; a session created on replica A is accepted on replica B; after logout the same cookie returns 401; the request built for C3 contains no `AccessContext` field.

---

### C1. Customer inquiry and answer

**Owner:** `InquiryService` (M2). **Caller:** customer browser. **Interface:** `POST /v1/inquiries` (CSRF required)
**Authorization:** `customer` (own inquiries only). Document scope derived server-side.

**Request**

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `question` | string | Yes | No | 1-1,000 chars after trim; no control characters |
| `conversation_id` | Uuid | No | Yes | Must belong to caller |

**Response 200**

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `inquiry_id` | Uuid | No | Server-generated. Customers use it for feedback (C6) and escalation (C4b). |
| `answer_id` | Uuid | Yes | Null unless a candidate answer was produced and passed validation |
| `status` | AnswerStatus | No | |
| `route` | Route | No | `ai`, `account_status` or `human_requested` |
| `answer_origin` | enum `ai_generated`, `account_status` | Yes | Null unless `answered`. `account_status` answers come from fixed templates, not a model. |
| `answer` | string | Yes | Only when `answered`; max 4,000 chars |
| `sources` | array of Source | No | Empty unless `answered` with `ai_generated`; max 8 |
| `clarification_prompt` | string | Yes | Only when `clarification_requested` |
| `escalation_offered` | boolean | No | True for `escalation_offered` and `temporarily_unavailable` |
| `suggested_reason` | EscalationReason | Yes | Prefill for C4 when escalation is offered |
| `configuration_version` | string | No | |
| `correlation_id` | Uuid | No | |
| `contract_version` | string | No | |

`Source = { ref: SourceRef, title, section_title, url }`. `url` resolves through C2b.

**Flow (Collins, Flow A; Vlad, Walkthrough A).**
1. Authenticate and build C9a; check CSRF.
2. Validate input; derive document scope.
3. **Decide `route` before applying admission** (`ai`, `account_status`, `human_requested`). The routing rule for `account_status` and for complexity is open (V22, V19).
4. Apply per-customer limit, then bounded admission. No queueing.
5. `account_status` route: call C7 and return a deterministic status answer. **No retrieval, no generation.**
6. `ai` route: retrieve (C2a), pre-generation evidence check (V19), generate (C3), validate (C10), return.

**Examples**

Supported answer:
```json
{
  "contract_version": "0.3",
  "inquiry_id": "b1d2c3e4-1111-4a22-8b33-9c44d55e6f77",
  "answer_id": "a9b8c7d6-3333-4c44-9d55-1e66f77a8899",
  "status": "answered",
  "route": "ai",
  "answer_origin": "ai_generated",
  "answer": "Install the Acme VPN client, sign in with your demo account, and select the 'Campus' profile.",
  "sources": [{
    "ref": { "source_id": "DOC-003", "section_id": "s2", "source_version": "3" },
    "title": "VPN Setup Guide",
    "section_title": "Installing the client",
    "url": "/v1/sources/DOC-003/sections/s2?version=3"
  }],
  "clarification_prompt": null,
  "escalation_offered": false,
  "suggested_reason": null,
  "configuration_version": "cfg-0.1",
  "correlation_id": "6f1c2a9e-3b7d-4d0a-9c11-2f5e8a7b1d42"
}
```

Provider failure, fallback offered (question preserved in the browser):
```json
{
  "contract_version": "0.3",
  "inquiry_id": "c2e3d4f5-2222-4b33-9c44-0d55e66f7788",
  "answer_id": null,
  "status": "temporarily_unavailable",
  "route": "ai",
  "answer_origin": null,
  "answer": null,
  "sources": [],
  "clarification_prompt": null,
  "escalation_offered": true,
  "suggested_reason": "provider_failure",
  "configuration_version": "cfg-0.1",
  "correlation_id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
}
```

Deterministic account status (fictional customer `CUST-004821`):
```json
{
  "contract_version": "0.3",
  "inquiry_id": "d3f4e5a6-3333-4c44-8d55-1e66f77a8899",
  "answer_id": "e4a5f6b7-4444-4d55-9e66-2f77a88b99cc",
  "status": "answered",
  "route": "account_status",
  "answer_origin": "account_status",
  "answer": "Your account is currently active.",
  "sources": [],
  "clarification_prompt": null,
  "escalation_offered": false,
  "suggested_reason": null,
  "configuration_version": "cfg-0.1",
  "correlation_id": "7b6a5948-3726-4150-8493-a2b1c0d9e8f7"
}
```

**Outcome and error mapping**

| Condition | Response |
|---|---|
| Invalid input | 400 `VALIDATION_FAILED` |
| No, invalid or expired session | 401 `UNAUTHENTICATED` |
| Missing or wrong CSRF token | 403 `CSRF_FAILED` |
| Conversation not caller's | 403 `FORBIDDEN` |
| Per-customer limit | 429 `RATE_LIMITED` + `Retry-After` |
| Aggregate admission bound or open circuit with no capacity to try | 503 `SERVICE_BUSY` + `Retry-After`. No queue; the browser keeps the question. |
| Insufficient, conflicting or stale evidence | 200 `clarification_requested` or `escalation_offered`, `suggested_reason: insufficient_evidence`; no unsupported answer shown |
| C10 validation fails (including the runtime evidence-support check) | 200 `clarification_requested` or `escalation_offered`, `suggested_reason: validation_failed`; candidate suppressed |
| Retrieval timeout or unavailable (C2a) | 200 `temporarily_unavailable`, `escalation_offered: true`, `suggested_reason: service_unavailable`. Not treated as proof that no source exists. |
| Provider failure (C3, any category including provider timeout and `circuit_open`) | 200 `temporarily_unavailable`, `escalation_offered: true`, `suggested_reason: provider_failure`; question preserved in the UI |
| Required customer context unavailable (C7) | 200 `escalation_offered`, `suggested_reason: service_unavailable` (controlled; no guessed customer facts) |
| Explicit human request recognized | 200 `escalation_offered`, `route: human_requested`, `suggested_reason: human_requested` |
| End-to-end deadline reached with no controlled outcome possible | 504 `DEADLINE_EXCEEDED` |

**Provider timeout versus 504 (Collins's question).**
- A provider timeout is a C3 `timeout` failure at the provider limit (V6, at most 12 s). It returns **200 `temporarily_unavailable`** inside the 20 s budget.
- `InquiryService` stops waiting on any dependency at deadline minus the fallback reserve (V28) and returns the controlled 200 fallback if it can.
- **504 `DEADLINE_EXCEEDED` is a backstop**, used only when the 20 s deadline passes before `InquiryService` can form any controlled outcome, for example a stalled non-provider dependency that never returned within the reserve. In normal operation the provider timeout fires first.
- A late provider result arriving after the fallback or 504 is discarded. It never replaces the response, never creates a support request, and never overwrites a newer inquiry in the browser (match results by `inquiry_id`).

*Closed with Collins's support (PR #17 review):* provider failure is 200 with a status; only admission overload is 503. Collins to confirm the 504 backstop wording and V28.

**Persistence.** The inquiry (status, route, source refs, `configuration_version`) is stored before responding. Question text storage is subject to the retention decision (V21). No general conversation-history persistence is assumed.
**Privacy.** The question goes to the provider through C3 only on the `ai` route; never logged. Account-status inquiries send nothing to the provider.

**Tests:** supported question returns `answered` with citations that resolve; unsupported returns `escalation_offered` with no answer; ambiguous returns `clarification_requested`; empty and oversized input return 400; no session returns 401; missing CSRF returns 403; other customer's conversation returns 403; provider timeout (mock) returns `temporarily_unavailable` in under 20 s; retrieval outage (mock) returns `service_unavailable`, not `insufficient_evidence`; 6th request in a minute returns 429; saturated admission returns 503 `SERVICE_BUSY` immediately with no queued request; stalled dependency past the deadline returns 504 and a late provider result does not replace the response; account-status question makes zero provider calls; `route` is present on every 200.

---

### C2. Retrieval and source access

**Owner:** `Retriever` (M3).

**C2a. `retrieve(ctx: AccessContext, query: str, top_k: int = 5, deadline_ms: int) -> RetrievalResult`**
**Caller:** `InquiryService` only.

| Input | Type | Constraints |
|---|---|---|
| `ctx` | AccessContext | Scope derived from `ctx.role` and `ctx.customer_scope`; the caller cannot widen it |
| `query` | string | 1-1,000 chars |
| `top_k` | int | 1-8 |
| `deadline_ms` | int | 1-2000 |

Output: `RetrievalResult { passages: [Passage], index_version: string }`, `Passage { ref: SourceRef, text (max 1,500 chars), score 0-1, rank int }`, sorted by rank. An empty list is valid and means **no permitted evidence was found**.
Failures: `RetrieverTimeout`, `RetrieverUnavailable`. `InquiryService` maps these to 200 `temporarily_unavailable` with `suggested_reason: service_unavailable`. A failure is never reported as an empty result.

**C2b. `GET /v1/sources/{source_id}/sections/{section_id}?version={n}`**
**Authorization:** any authenticated role, within scope. Scope and access are rechecked on every open (Vlad, step A8). `version` optional (default current). Returns `{ ref, document_title, section_title, text, correlation_id, contract_version }`.

| Condition | Response |
|---|---|
| Malformed ID | 400 `VALIDATION_FAILED` |
| Missing, removed, access changed, or out of scope | 404 `NOT_FOUND` (identical response, so restricted documents are not revealed and no passage is silently substituted) |
| Store unavailable | 503 `DEPENDENCY_UNAVAILABLE` |

**Tests:** known section returns 200; old version still resolves when retained; removed source returns 404; agent-only source requested by a customer returns 404; access revoked between answer and click returns 404; empty retrieval returns an empty list; retriever timeout (mock) raises `RetrieverTimeout` and C1 reports `service_unavailable`.

---

### C3. AI generation adapter

**Owner:** `GenerationAdapter` (M4). It translates between the internal request and the provider, normalizes results and errors, enforces deadlines and call limits, and coordinates shared breaker state through M9. It does **not** authorize, save requests, or validate citations (that is C10).
**Method:** `generate(request: GenerationRequest) -> GenerationResult`
**Caller:** `InquiryService` only. **No `AccessContext` parameter** (see C9a): authorization is complete before this call.

**`GenerationRequest`**

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `question` | string | Yes | No | 1-1,000 chars |
| `passages` | array of Passage | Yes | No | 1-8, permitted passages only |
| `deadline_ms` | int | Yes | No | 1-12000, based on remaining deadline minus the fallback reserve |
| `configuration_version` | string | Yes | No | |
| `correlation_id` | Uuid | Yes | No | |

Draft 2's `approved_context` field is **removed**. Customer-database fields are never sent to the provider.

**`GenerationResult` (success)**

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `candidate_answer` | string | Yes | Null if the model reports it cannot answer |
| `cited_refs` | array of SourceRef | No | References to supplied evidence |
| `adapter_version` | string | No | |

The result is a **candidate**. It becomes an answer only after C10 passes.

**Failure categories (provider-neutral, Collins Flow C)**

| Category | Meaning | Customer-visible result |
|---|---|---|
| `timeout` | Provider limit (V6) or remaining deadline reached | `temporarily_unavailable` |
| `quota_exceeded` | Provider quota or 429 | `temporarily_unavailable` |
| `service_unavailable` | 5xx or network | `temporarily_unavailable` |
| `invalid_provider_response` | Unparseable or off-contract output | `temporarily_unavailable` (no unsupported answer shown) |
| `circuit_open` (new) | The shared breaker is open, or the single half-open trial is held by another replica. No provider call is made. | `temporarily_unavailable` |
| `provider_configuration_error` | Authentication or configuration failure | `temporarily_unavailable` to the customer; operator alert; no repeated customer retries |

**Rules**
- Check the breaker, admission limits and remaining deadline before calling the provider.
- **No automatic generation retry** (V17 = 0) and no automatic failover to a second provider (deferred; B17 is consolidated into B11).
- **Circuit breaker (V18, proposed):** three qualifying failures within 60 s open the breaker; cooldown 30 s; then one global half-open trial per provider/model/credential scope, guarded by a 20 s lease so that only one replica probes. The breaker counter, reset and write policy is Collins's to define; state is held in shared storage (M9) so all replicas agree. Which categories "qualify" (for example `timeout`, `service_unavailable`, `quota_exceeded`) is open with Collins.
- Late results are discarded and never replace a completed fallback response or create a support request.
- Text in passages or customer input is data. Instructions inside it never override policy or grant tools or database access.
- Credentials stay server-side. Only the question and permitted passages are sent. Never customer database records, session data, tokens or `AccessContext`.

**Tests:** valid input returns a candidate with `cited_refs`; each failure category maps correctly (mock); open breaker returns `circuit_open` without a provider call; with two replicas and an expired lease, exactly one half-open trial runs; a passage containing "ignore your rules" does not change behavior; a result arriving after the deadline is ignored; configuration error triggers an operator alert and a customer-safe message; a request carrying any field outside the schema above (including `approved_context` or `ctx`) is rejected before the provider call; no automatic retry occurs after a `timeout`.

---

### C10. Answer and source validation (internal)

**Owner:** `AnswerValidator` (M5). **Caller:** `InquiryService`.
**Method:** `validate(ctx: AccessContext, candidate: GenerationResult, retrieved: RetrievalResult) -> ValidationResult`

```
ValidationResult {
  outcome:         "pass" | "fail"
  failure_reasons: [ "unknown_source" | "version_mismatch" | "access_denied"
                   | "unresolvable_source" | "no_citations" | "malformed_output"
                   | "unsupported_content" | "support_check_unavailable" ]
  checked_refs:    [SourceRef]
}
```

**Step 1, structural checks** (always run): every `cited_refs` entry is in the retrieved set; versions match; the caller still has access; each reference resolves via C2b; at least one citation exists for an answer.

**Step 2, runtime evidence-support check** (new; Collins's point 2). Runs **only if Step 1 passes**:
- Interface: `EvidenceSupportPolicy.check(candidate_answer, cited_passages) -> SupportResult { supported: boolean, unsupported_spans: [{ start: int, end: int }] }`. Its inputs are the candidate text and the **cited passage texts only**. It receives no `AccessContext`, no customer data, and it makes no provider call unless Collins's rule explicitly requires one (open).
- The **rule itself** (how support is decided, thresholds, whether it may use a second model call) is Collins's and tracked as V19. This contract fixes only where it plugs in and how failure is handled.
- `supported = false` gives `fail` with `unsupported_content`.
- If the policy cannot run (timeout, error, no rule configured), **fail closed**: `fail` with `support_check_unavailable`. A candidate is never shown without a completed check.
- A model's self-reported confidence is not accepted as proof.

**Limit:** these checks reduce, but do not eliminate, unsupported answers. A valid link is not proof of correctness (Gao et al., as cited in the pitch). Offline manual scoring in B12 remains the measure of answer support and is separate from the runtime check.

**On `fail`:** the candidate is suppressed, `answer_id` stays null, and C1 returns `clarification_requested` or `escalation_offered` with `suggested_reason: validation_failed`. Retrying generation is **not** attempted (V17 = 0).

**Tests:** unknown source ID gives `fail/unknown_source`; stale version gives `fail/version_mismatch`; source removed after retrieval gives `fail/unresolvable_source`; access revoked gives `fail/access_denied`; answer with no citations gives `fail/no_citations`; real citations plus a claim not in the passages (fixture) gives `fail/unsupported_content`; policy timeout (mock) gives `fail/support_check_unavailable` and no answer is shown; all-valid and supported gives `pass`.

---

### C4. Human escalation

**Owner:** `EscalationService` (M6). **Authorization:** `customer` (own records). All `POST` endpoints require CSRF.

**Design (D09/D17, Vlad's walkthrough B2-B6).** The server issues and registers each `submission_id` when the support form opens. The ID is bound to the customer and the operation. Registration alone creates **no** human-visible support request. A submit then atomically creates the request and a completed receipt under one unique identity. Disabling the submit button is a usability measure only, never the mechanism.

#### C4a. `POST /v1/escalations/submission-ids` (register an ID)

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `operation` | enum `escalation` | Yes | Only value in this draft. Binds the ID to this operation. |

**Response 201**

| Field | Type | Notes |
|---|---|---|
| `submission_id` | Uuid | Server-issued |
| `operation` | string | Echoed |
| `registration_state` | RegistrationState | `unused` |
| `expires_at` | Timestamp | Registration time plus V25 |
| `correlation_id`, `contract_version` | | |

| Condition | Response |
|---|---|
| More than V25's outstanding unused IDs | 429 `RATE_LIMITED` |
| Escalation capacity bound | 503 `SERVICE_BUSY` |
| Storage down | 503 `DEPENDENCY_UNAVAILABLE` |

Cancel needs no endpoint: an unused ID simply expires. A deliberate new request always starts with a new C4a call. Retries never obtain a replacement automatically.

#### C4b. `POST /v1/escalations` (submit)

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `submission_id` | Uuid | Yes | No | Must be a registered ID owned by the caller, bound to `escalation` |
| `reason` | EscalationReason | Yes | No | |
| `inquiry_id` | Uuid | No | Yes | Null when the customer requests a human directly; if present, must belong to caller |
| `content` | string | Yes | No | 1-1,000 chars; the customer-reviewed text (the prefilled question is only a suggestion) |
| `note` | string | No | Yes | 0-2,000 chars |
| `consent_to_share` | boolean | Yes | No | Must be `true` |

Unrelated conversation history is **not** attached automatically.

**Response 201 (new) / 200 (replay of a completed receipt with the same payload)**

| Field | Type | Notes |
|---|---|---|
| `request_id` | Uuid | The saved request |
| `submission_id` | Uuid | Echoed |
| `state` | RequestState | `queued` on first creation. On replay, the request's **current** state. |
| `created_at` | Timestamp | |
| `acknowledgement` | string | Returned only after the durable commit. States that the request was saved, not that an agent has read or accepted it, and gives no response-time promise. |
| `correlation_id`, `contract_version` | | |

**Example request**
```json
{
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "reason": "insufficient_evidence",
  "inquiry_id": "b1d2c3e4-1111-4a22-8b33-9c44d55e6f77",
  "content": "The 'Campus' VPN profile is missing after install.",
  "note": "Tried reinstalling twice.",
  "consent_to_share": true
}
```

**Example 201 response**
```json
{
  "contract_version": "0.3",
  "request_id": "f6a7b8c9-5555-4e66-8f77-3a88b99cc0dd",
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "state": "queued",
  "created_at": "2026-11-01T15:04:05Z",
  "acknowledgement": "Your request has been saved. It has not been read by an agent yet.",
  "correlation_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
}
```

**Example error (expired unused ID)**
```json
{
  "contract_version": "0.3",
  "error": {
    "code": "SUBMISSION_ID_EXPIRED",
    "message": "This form timed out before it was sent. Your text is still here; please send it again.",
    "retryable": false,
    "correlation_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
  }
}
```

**Submit decision table (Vlad's B3, B4, B6)**

| Situation | Behavior |
|---|---|
| Registered, unused, owned by caller, valid payload | In **one transaction**: create the support request and the completed receipt under the unique key `(customer_scope [or tenant + customer], operation, submission_id)`. Returns 201. |
| Same ID, completed receipt, **same** payload hash | 200 with the original `request_id`; no second record |
| Same ID, completed receipt, **different** content | 409 `CONFLICT`; nothing changes. A genuinely new request needs a new C4a ID. |
| Unused ID past its validity (V25) | 410 `SUBMISSION_ID_EXPIRED`. The server does **not** recreate or silently replace it. The UI keeps the editable content and calls C4a again. |
| Unknown ID, ID of another customer, or ID bound to another operation | 404 `NOT_FOUND` (identical response; no cross-customer receipt lookup) |
| 20 concurrent submits with the same ID | One transaction commits (unique constraint). The rest return 200 replay or wait and then replay. Exactly one row. |
| Validation fails | 400 `VALIDATION_FAILED` with field names; UI keeps content; no receipt claimed |
| Save **known** to have failed | 503 `DEPENDENCY_UNAVAILABLE`, "not saved"; nothing stored; retry with the **same** ID while it is unexpired |
| Commit outcome **uncertain** (timeout after commit started) | 503 `SAVE_OUTCOME_UNCERTAIN`, "confirmation unavailable". UI calls C4c or retries C4b with the same ID. The server never says that no record exists. |
| Save succeeded, acknowledgment lost | Retry or C4c returns the completed receipt |
| `consent_to_share` is false | 400 `VALIDATION_FAILED` |
| `inquiry_id` not caller's | 403 `FORBIDDEN` |
| Per-customer submit limit (V9) | 429 `RATE_LIMITED` |
| Escalation capacity bound | 503 `SERVICE_BUSY` (separate from generation capacity) |
| Provider returned late for the originating inquiry | No effect. A support request is never created automatically. |

**Payload binding.** The receipt stores a hash of the canonical payload (`reason`, `inquiry_id`, `content`, `note`, `consent_to_share`) so same-content detection does not require comparing stored text. The receipt is created in the same transaction as the request.

**Persistence.** The stored request is the source of truth. If a queue broker is used, a transactional outbox (or equivalent) prevents loss between commit and publish. A C7 outage never blocks escalation: the request is saved with the `customer_id` from trusted context and enriched later. Completed receipts are retained for V11.
**Stored fields:** reviewed content, customer reference (from the trusted context), reason, originating inquiry reference, `submission_id`, payload hash, timestamps, `state`, `version`, assigned agent.
**Privacy.** Content and note are not logged and are not sent to the AI provider.

#### C4c. `GET /v1/escalations/{submission_id}` (status, for reconciliation)

Customer, own records only. Returns:

| Field | Type | Notes |
|---|---|---|
| `submission_id` | Uuid | |
| `registration_state` | RegistrationState | `unused`, `completed` or `expired` |
| `saved` | boolean | True only when a completed receipt exists |
| `request_id` | Uuid | Null unless `saved` |
| `state` | RequestState | Null unless `saved` |
| `created_at` | Timestamp | Null unless `saved` |
| `expires_at` | Timestamp | Null when `completed` |

Unknown ID or another customer's ID: 404 `NOT_FOUND`. This lets the UI reconcile after a lost acknowledgment without risking a duplicate.

#### C4d. `POST /v1/escalations/{request_id}/replies` (customer reply)

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `message` | string | Yes | 1-2,000 chars |
| `expected_version` | int | Yes | The request `version` the customer saw when it was in `waiting_customer` |

Customer, own record only.

| Situation | Response |
|---|---|
| Request is `waiting_customer` and `expected_version` matches | 201. Stores the reply, moves the request to `in_review`, increments `version`. |
| Duplicate: same `expected_version` and same message already accepted | 200 with the stored reply; no second message (V29) |
| Same `expected_version`, different message, already accepted | 409 `CONFLICT` |
| Request is `resolved` (late reply) | 409 `CONFLICT`. Resolved is terminal. A late reply does not reopen it; the customer starts a new request through C4a. |
| Any state other than `waiting_customer` | 409 `CONFLICT` |
| Another customer's request | 404 `NOT_FOUND` |

**Tests:** register returns an unused ID with `expires_at`; fourth outstanding unused ID returns 429; first submit returns 201; same-ID retry returns 200 with one stored row; 20 concurrent same-ID submits create exactly one row; same ID with different content returns 409; unused ID after V25 returns 410 and no row is created, and the same ID is not usable later; unknown ID returns 404; another customer's ID returns 404 and reveals nothing; save failure (mock) returns 503 `DEPENDENCY_UNAVAILABLE`, no row, and the same-ID retry succeeds later; commit-then-timeout (mock) returns 503 `SAVE_OUTCOME_UNCERTAIN` and C4c then returns `saved: true`; lost acknowledgment followed by C4c returns the saved request; `consent_to_share: false` returns 400; another customer's `inquiry_id` returns 403; administrator calling C4 returns 403; duplicate reply returns 200 with one stored message; reply on a `resolved` request returns 409 and the request stays `resolved`; replica B accepts a C4b retry for an ID registered on replica A.

---

### C5. Agent review and update

**Owner:** `AgentQueueService` (M6). **Authorization:** `agent` only. Customers and administrators get 403. All `POST` endpoints require CSRF.

**C5a. `GET /v1/agent/escalations?state=queued&limit=25&cursor=...`**
`state` is optional. `limit` 1-100, default 25. Returns `{ items: [EscalationSummary], next_cursor|null, correlation_id, contract_version }` with `EscalationSummary { request_id, state, content, reason, created_at, assigned_agent_id|null, customer_ref, account_status|null, version }`. Customer data is limited to the C7 allowlist (`customer_id`, `account_status`). `account_status` is null when C7 is unavailable.

**C5b. `POST /v1/agent/escalations/{request_id}/claim`**
No body. Atomic: succeeds only if `state = queued`; sets `assigned`, `assigned_agent_id = caller`, increments `version`, and returns the updated summary. If another agent claimed first, 409 `CONFLICT`.

**C5c. `POST /v1/agent/escalations/{request_id}/transition`**

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `to_state` | RequestState | Yes | Must be allowed below |
| `expected_version` | int | Yes | Optimistic check; mismatch returns 409 |
| `message_to_customer` | string | Cond. | Required for `waiting_customer`; 1-2,000 chars |
| `resolution_note` | string | Cond. | Required for `resolved`; 1-2,000 chars |
| `release_reason` | string | Cond. | Required for `queued` (release); 1-500 chars |

**Permitted transitions (proposed; Hanlin and David to review)**

| From | To | Who | Extra field |
|---|---|---|---|
| `queued` | `assigned` | Any agent (via claim) | |
| `assigned` | `queued` (release) | Assigned agent | `release_reason` |
| `assigned` | `in_review` | Assigned agent | |
| `in_review` | `waiting_customer` | Assigned agent | `message_to_customer` |
| `waiting_customer` | `in_review` | System (customer reply, C4d) or assigned agent | |
| `in_review` | `resolved` | Assigned agent | `resolution_note` |
| `resolved` | none | Terminal; late customer replies do not reopen it | |

Any other transition, a non-owner update, or a stale version returns 409 `CONFLICT`. Conflicting updates never silently overwrite each other (atomic owner and version check).

| Other conditions | Response |
|---|---|
| Not an agent | 403 `FORBIDDEN` |
| Missing CSRF token | 403 `CSRF_FAILED` |
| Unknown `request_id` | 404 `NOT_FOUND` |
| Missing conditional field | 400 `VALIDATION_FAILED` |
| Storage down | 503 `DEPENDENCY_UNAVAILABLE` |

**Audit.** Each transition records agent ID, old and new state, `correlation_id`, and timestamp, not content. A release also records that a reason was given, not its text.

**Tests:** customer or administrator on any C5 endpoint returns 403; two concurrent claims give one 200 and one 409; non-owner transition returns 409; `resolved` then any transition returns 409; stale version returns 409; `waiting_customer` without a message returns 400; release without `release_reason` returns 400; release returns the request to `queued` and a second agent can claim it; customer reply moves the request back to `in_review`; saved request visible in queue after a simulated broker failure; C7 outage still lists requests with `account_status: null`.

---

### C6. Feedback and reviewed improvement

**Owner:** `FeedbackService` (M8). Learning is a **reviewed** loop. Feedback is evidence, not an instruction to the model and not an automatic training signal.

**C6a. `POST /v1/feedback`** (customer, CSRF required)

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `inquiry_id` | Uuid | Yes | No | Must belong to caller. Feedback is keyed to the **inquiry**. |
| `answer_id` | Uuid | No | Yes | **Null allowed** (Collins's point 3). Null when the inquiry produced no answer (fallback, validation failure, provider failure, excessive escalation). If present, must belong to that inquiry. |
| `rating` | enum `helpful`, `not_helpful` | Yes | No | |
| `category` | enum `incorrect`, `incomplete`, `wrong_source`, `unclear`, `too_much_escalation`, `fallback_unhelpful`, `other` | No | Yes | Only with `not_helpful`. `incorrect`, `incomplete`, `wrong_source` require a non-null `answer_id`. |
| `comment` | string | No | Yes | 0-500 chars |

The server records the inquiry's **outcome** (`answered`, `clarification_requested`, `escalation_offered`, `temporarily_unavailable`), its `route`, source refs (if any) and `configuration_version` with the feedback. The browser does not supply them.

Response 201: `{ feedback_id, state: "pending_review", correlation_id, contract_version }`.

**Example (feedback on a fallback with no answer)**
```json
{
  "inquiry_id": "c2e3d4f5-2222-4b33-9c44-0d55e66f7788",
  "answer_id": null,
  "rating": "not_helpful",
  "category": "fallback_unhelpful",
  "comment": "I only needed the VPN steps."
}
```

**Feedback window (D05, V26).** Feedback is accepted for V26 (7 days) after the inquiry. Later submissions return 409 `FEEDBACK_WINDOW_CLOSED`. *Assumption to confirm with Vlad:* "feedback expiry" in issue #12 means this submission window. Retention of stored feedback is separate and open (V21).

**C6b. `GET /v1/agent/feedback?state=pending_review&limit=25`** (agent with reviewer permission) lists feedback with outcome, route, source and configuration versions.

**C6c. Improvement proposals** (agent with reviewer permission; all `POST` require CSRF)

| Endpoint | Purpose |
|---|---|
| `POST /v1/agent/improvements` | Propose a bounded change: `{ type: "knowledge_source"\|"retrieval"\|"prompt"\|"configuration", description (1-2,000), linked_feedback_ids (1-50) }` |
| `POST /v1/agent/improvements/{id}/review` | **Independent** reviewer approves or rejects, and records privacy-impact notes: `{ decision: "approve_for_evaluation"\|"reject", privacy_note (1-1,000) }`. Reviewer must differ from the proposer (else 409 `CONFLICT`). |
| `POST /v1/agent/improvements/{id}/evaluation` | Record the result against the fixed baseline: `{ baseline_id, report_ref, passed: boolean }` |
| `POST /v1/agent/improvements/{id}/release` | Allowed only if evaluation passed. Requires `rollback_ref`. Creates a new `configuration_version`. |
| `POST /v1/agent/improvements/{id}/rollback` | Restores the prior version; records reason |

**How a release takes effect (Vlad's M8).** Approved source changes enter through M3 using the C8 document-administration boundary. Approved generation or prompt configuration is applied through M4. Neither path lets feedback change production behavior directly.

**Proposal states:** `proposed`, `approved_for_evaluation`, `evaluated`, `released`, `rejected`, `rolled_back`. Skipping a state returns 409 `CONFLICT`.
A malicious or mistaken rating cannot change production behavior directly. It can only create review evidence.

| Condition | Response |
|---|---|
| Invalid enum, `category` with `helpful`, comment too long | 400 `VALIDATION_FAILED` |
| Category requiring an answer but `answer_id` null | 400 `VALIDATION_FAILED` |
| Inquiry or answer not the caller's | 403 `FORBIDDEN` |
| Duplicate feedback for the same `(inquiry_id, answer_id or null)` | 409 `CONFLICT` |
| Outside the feedback window | 409 `FEEDBACK_WINDOW_CLOSED` |
| Customer or administrator on agent endpoints | 403 `FORBIDDEN` |
| Release without a passed evaluation or `rollback_ref` | 409 `CONFLICT` |

**Privacy.** Comments are visible only to authorized reviewers. Aggregates minimize identifiers. Raw feedback is not placed in the public repository. Retention: V21, open. Comments are not logged and not sent to the provider.
*Open (Vlad, Collins):* which role approves a release. Vlad's M8 text says he coordinates release and rollback approval; this draft assumes agents with reviewer permission for proposals and reviews, and administrators do not see feedback content. Vlad to confirm.

**Tests:** valid feedback with an answer returns 201 with versions stored; feedback with `answer_id: null` on a fallback inquiry returns 201; `incorrect` with null `answer_id` returns 400; duplicate returns 409; feedback after V26 returns 409 `FEEDBACK_WINDOW_CLOSED`; the same person proposing and reviewing returns 409; release without evaluation returns 409; harmful proposal fails evaluation and cannot be released; rollback restores the prior `configuration_version`; administrator reading feedback returns 403.

---

### C7. Existing customer database

**Owner:** `CustomerDirectoryAdapter` (M7). Read-only in this draft. No real system is connected; the adapter is specified against a fictional "CustomerDB". The AI provider has no direct database connection and never receives customer-database fields.
**Method:** `get_customer_profile(ctx: AccessContext, customer_id: str, deadline_ms: int) -> CustomerProfile`
**Callers:** `InquiryService` (account-status route), `EscalationService` and `AgentQueueService` (enrichment). The `customer_id` must equal `ctx.customer_scope` for a customer; agents may look up the customer of a request they hold.

| Input | Constraints |
|---|---|
| `customer_id` | `^CUST-[0-9]{6}$`, e.g. `CUST-004821` |
| `deadline_ms` | 1-2000 |

**`CustomerProfile` (allowlist, V22):** `customer_id`, `account_status` (`active`, `suspended`). Excluded: display name, tier, email, phone, address, payment and credential data. Draft 2 also allowed `display_name` and `tier`; Draft 3 removes them to match Vlad's minimum-field design. Adding a field requires a team decision.

| Condition | Behavior |
|---|---|
| Bad ID format | `InvalidCustomerId` (400) |
| ID outside caller's scope | `AccessDenied` (403) |
| Not found | `CustomerNotFound` (404) |
| Timeout or database down | `CustomerDirectoryUnavailable` |

**Failure handling**
- Account-status inquiries (`route: account_status`) return a **deterministic** answer from `account_status` using fixed templates. No model generation. If C7 fails, C1 returns 200 `escalation_offered` with `suggested_reason: service_unavailable` and states no customer fact.
- General questions need no lookup and proceed without it.
- `EscalationService` always saves the request using the `customer_id` from trusted context, and enriches it later. A C7 outage never blocks escalation.
- Optional cache (proposed, open): keyed by customer and scope, short-lived, and invalidated on access change.
- *Open (Vlad):* whether any update operation is ever permitted. Draft assumes none.

**Tests:** valid ID returns only `customer_id` and `account_status`; ID outside scope is denied; not found raises `CustomerNotFound`; timeout (mock) raises `CustomerDirectoryUnavailable`, escalation still saves, and an account-status inquiry returns the controlled escalation offer; the C3 request never contains customer-database fields; an account-status inquiry produces no provider call.

---

### C8. Document administration

**Owner:** `DocumentService` (M3). **Authorization:** `administrator` only. All state-changing endpoints require CSRF. Administrators cannot read customer conversations, escalations, or feedback content through any of these endpoints.

| Endpoint | Purpose |
|---|---|
| `POST /v1/admin/documents` | Create a document |
| `PUT /v1/admin/documents/{source_id}` | Replace a document. Creates a new `source_version`; prior versions retained so citations still resolve |
| `POST /v1/admin/documents/{source_id}/retire` | Retire a document; new retrievals exclude it, and C2b returns 404 for retired sections after the retention window (open) |
| `GET /v1/admin/documents` | List documents (`limit` 1-100) |

This is also the entry point for source changes approved through the C6 improvement process (`type: knowledge_source`).

**Create/replace body**

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `title` | string | Yes | 1-120 chars |
| `visibility` | enum `customer`, `agent` | Yes | Controls retrieval scope |
| `sections` | array of `{ section_id, title, text }` | Yes | 1-30 sections; `section_id` matches `^s[0-9]{1,2}$` and is unique; `text` 1-5,000 chars |

Response: `{ source_id, source_version, index_status: "rebuilding"|"ready", correlation_id, contract_version }`. Source IDs stay stable across versions. Invalid input is rejected.

| Condition | Response |
|---|---|
| Invalid body, duplicate `section_id` | 400 `VALIDATION_FAILED` |
| Not an administrator | 403 `FORBIDDEN` |
| Missing CSRF token | 403 `CSRF_FAILED` |
| Unknown `source_id` | 404 `NOT_FOUND` |
| Index rebuild fails | 503 `DEPENDENCY_UNAVAILABLE`; previous version stays active |

**Tests:** replace creates version 4 while `DOC-003` v3 still resolves; invalid section ID returns 400; customer or agent calling C8 returns 403; failed rebuild leaves the prior version active; retired document no longer retrieved.

---

## 5. Test coverage by risk (for David)

| Risk | Contracts |
|---|---|
| Cross-customer access | C1, C4, C5, C6, C7, C9 |
| Administrator over-reach | C4, C5, C6, C9 |
| Session expiry, logout, replica sharing, CSRF | C9 and every state-changing endpoint |
| Invalid, stale or unsupported citations | C2, C10 |
| Provider failure, late results, config errors | C1, C3 |
| Circuit breaker concurrency across replicas | C3 |
| Duplicate, expired, unknown or lost escalation ID | C4 |
| Uncertain commit versus known failed save | C4 |
| Duplicate or late customer replies | C4d |
| Concurrent claim and stale updates | C5 |
| Malicious feedback or prompt injection | C3, C6 |
| Feedback with no answer; feedback window | C6 |
| Overload, bounded admission, no AI queue | C1, C3, C4 |
| Service level (95% within 15 s, denominator-aware) | C1 (`route`, outcome status) |
| Required customer data unavailable | C1, C7 |
| Customer data never reaches the provider | C3, C7 |

---

## 6. Changes from Draft 2

| Draft 2 | Draft 3 |
|---|---|
| `submission_id` generated by the browser | Server-issued and pre-registered via new C4a; bound to customer and operation; expiry V25 |
| C4a submit, C4b status, C4c reply | Renumbered: C4a register, C4b submit, C4c status, C4d reply |
| Reused ID with unknown or expired state undefined | 410 `SUBMISSION_ID_EXPIRED` (never recreated); unknown or foreign ID is 404; uncertain commit is 503 `SAVE_OUTCOME_UNCERTAIN` |
| 24 h idempotency retention (V11, open) | Receipt retained for request lifetime plus 30 days after resolution |
| Customer reply allowed only in `waiting_for_customer` | Renamed `waiting_customer`; replies carry `expected_version`; duplicate reply replays; late reply on `resolved` returns 409 |
| Release to `queued` with no reason | `release_reason` required |
| `Authorization: Bearer` on all endpoints | Cookie session, CSRF token, session expiry, logout (C9b) |
| `AccessContext` before every internal call | Same, with an explicit C3 exception: no context reaches the provider adapter |
| `approved_context` in C3; C7 allowlist of four fields | `approved_context` removed; C7 allowlist is `customer_id` and `account_status`; account status is deterministic and bypasses the model |
| Customer-context lookup then generation | New `route` decided before admission; `answer_origin` added |
| V6 provider timeout 15 s; V17 retry 0 or 1 | 12 s; no automatic retry (V17 = 0) |
| V16 queue size and wait limit; queue wait counts in the deadline | No AI waiting queue; immediate `SERVICE_BUSY` |
| V18 breaker open | Vlad's proposal recorded; `circuit_open` failure category added; counter, reset and write policy remains Collins's |
| C10 structural checks only | Adds runtime evidence-support hook (`EvidenceSupportPolicy`), fail-closed `support_check_unavailable` and `unsupported_content`; rule remains Collins's (V19) |
| C6 required `answer_id` | `answer_id` nullable; feedback keyed to `inquiry_id` and outcome; category `fallback_unhelpful`; 7-day window and `FEEDBACK_WINDOW_CLOSED` |
| 504 vs provider failure unclear | Provider timeout is 200 `temporarily_unavailable`; 504 is a backstop with a fallback reserve (V28) |
| `EscalationReason` without a service-failure reason | Adds `service_unavailable` so retrieval or customer-data failure is distinct from `insufficient_evidence` |
| No service target | Section 2.7 service level (V27) with eligibility denominator and load scenarios |
| Retrieval failure unspecified | Mapped to `service_unavailable`, never to an empty result |
| `contract_version` `"0.2"` | `"0.3"` |

---

## 7. Open decisions

1. **Vlad:** tenant model (V20); peak factor and generation concurrency (V14, V15); identity provisioning and whether logout of all sessions exists; whether C7 is strictly read-only; who approves improvement releases; confirm session expiry (V23, V24), unused-ID validity (V25) and the meaning of "feedback expiry" (V26).
2. **Collins:** confirm 504 as a backstop and the fallback reserve (V28); circuit-breaker counter, reset, write policy and which failures qualify (V18); the runtime evidence-support rule and the pre-generation sufficiency rule (V19); confirm zero retries (V17); provider and model quota evidence.
3. **David:** whether `subject_id` may be logged; retention (V21) and the 30-day receipt retention (V11); review the transition table, reply-version rule (V29) and the verification plan, including denominator-aware service-level tests.
4. **Team:** which inquiries use `account_status` and which need customer context (V22); how `route` is decided (account-status, complexity and explicit human request); confirm all proposed values; record decisions in `decisions.md`.
5. **Diagram:** component names and the C8-C10 interactions must appear exactly as named here, including the session store, receipt store and breaker state held through M9.

## 8. Contribution note

## Hanlin Wang

**Role:** Lead for interface contracts (C1-C10).

**What I did**
- Drafted the interface contracts, including shared conventions, error codes, and the proposed-values table (Drafts 1 and 2).
- Revised Draft 2 into Draft 3 after reading Vlad's Nov 1 architecture review, the follow-up in issue #12, and Collins's review on PR #17. Changes are listed in Section 6.
- Reworked escalation around server-issued submission IDs (C4), added session and CSRF behavior (C9b), nullable feedback `answer_id` (C6), and the runtime evidence-support hook (C10).
- Listed open decisions for Vlad, Collins, and David in Section 7.

**Reviews**
- Requested review from Collins (interfaces) and David (verification). Vlad checks architecture consistency. Collins has commented on Draft 2; his points are addressed in Draft 3 and need his confirmation.

**Tools used**
- I used an AI assistant (Claude) to help draft and structure the contracts. I reviewed the content and checked it against the team documents.

**Not yet done / limits**
- All limits are proposals pending team approval.
- No implementation or testing has been done. This is a design specification.
