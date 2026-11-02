# DeskGuide Interface Contracts (Draft 3.1, aligned to the Nov 1 architecture review, the decisions log D01-D21 and PR #17 feedback)

**Lead:** Hanlin | **Reviewers:** Collins (interfaces), David (verification) | **Architecture check:** Vlad
**Status:** Draft 3.1 for review. Revises Draft 3 to match Vlad's decisions log (revision 4, Nov 1: D01-D21), his architecture review, and Collins's review on PR #17. All limits are **proposed**, not team-approved. No implementation, provider access, or measured capacity is claimed. All examples are fictional. *Source limits:* PR #16 (Collins) and PR #18 (David) were opened but their files did not load, so David's session and unused-ID recommendations and Collins's evidence and breaker details are **not** incorporated (see Section 7).
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
| C4 | Human escalation | C4a `POST /v1/escalations/submission-ids`, C4b `POST /v1/escalations`, C4c `GET /v1/escalations/{submission_id}`, C4d `POST /v1/escalations/{request_id}/reply-ids`, C4e `POST /v1/escalations/{request_id}/replies` | B11, R2 |
| C5 | Agent review and update | `GET /v1/agent/escalations`, `.../{request_id}/claim`, `.../{request_id}/transition` | B13, R2 |
| C6 | Feedback and reviewed improvement | feedback and improvement-proposal endpoints | B13, B16, P04, R3 |
| C7 | Existing customer database | `get_customer_profile()` | P02, R5 |
| C8 | Document administration | `/v1/admin/documents` | B14 |
| C9 | Access context and session | `AccessContext` type (C9a); `GET /v1/session`, `POST /v1/session/logout` (C9b) | B09, all |
| C10 | Answer and source validation | `validate()` | B07, B10 |

Note: Draft 2 called the escalation status lookup C4b and the customer reply C4c. Draft 3 inserted ID registration as C4a. Draft 3.1 also registers reply IDs (C4d) and renames the reply submit C4e (see Section 6).

---

## 2. Shared conventions

**Roles (server-derived, never trusted from the browser):** `customer`, `agent`, `administrator`.
Administrator rights cover document administration (C8) only. They do **not** grant access to customer conversations, escalations, or raw feedback (C4, C5, C6 content).

**Enum style.** Enum values are lowercase snake_case, matching Collins's flows. Error codes are UPPER_SNAKE.

**Versioning.** `/v1/` path prefix. Responses include `contract_version` (currently `"0.3.1"` while drafting).

### 2.1 Authentication, session and CSRF (D18)

Vlad's architecture uses opaque server-side sessions in cookies. Draft 2's bearer-token header is removed.

| Item | Rule |
|---|---|
| Session credential | Opaque session identifier in a cookie with `Secure`, `HttpOnly`, `SameSite=Lax`. The browser never reads it. Session records live in shared storage (M9), not in one replica's memory. |
| Identity source | The server derives role and `customer_scope` from the session record. Nothing about identity is read from request bodies, query strings or headers. |
| Login | The session identifier is **rotated at login**, and invalidated at logout. An established server-side session library is used rather than default client-side Flask sessions (D18). |
| CSRF | Every state-changing request (`POST`, `PUT`, `DELETE`) must carry `X-CSRF-Token` matching the token bound to the session. Mismatch or absence returns 403 `CSRF_FAILED`. `GET` requests never change state. |
| Expiry | Idle expiry V23 and absolute expiry V24 (both **proposed by Hanlin**; David is asked to recommend final lifetimes, renewal and cleanup). An expired or unknown session returns 401 `UNAUTHENTICATED`. The server never silently extends a session past the absolute limit. |
| Logout | `POST /v1/session/logout` invalidates the current session record server-side. Scope is the current session only (proposed). Whether a separate all-sessions logout exists is Vlad's decision after David's input (D18). |
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
| `submission_id` | One intentional customer submission, either a new escalation or one reply to a request. **Issued and registered by the server** (C4a, C4d), bound to the customer and the operation. Reused only for retries of the same submission. | **Server** (Draft 2: browser) |
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
| `RequestState` | `queued`, `assigned`, `in_review`, `waiting_for_customer`, `resolved`. Follows the decisions log (D12, D17), Collins's model and Draft 2. Vlad's architecture review spells the fourth state `waiting_customer`; Vlad to reconcile (Section 7). |
| `RegistrationState` | `unused`, `completed`, `expired` |

### 2.5 Error envelope (all non-2xx)

```json
{
  "contract_version": "0.3.1",
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
| `NOT_FOUND` | 404 | No | Missing, purged, unknown, or outside caller's scope (same response for all). Includes unknown or foreign submission IDs and feedback on an inquiry whose metadata expired. |
| `CONFLICT` | 409 | No | Illegal transition, ownership/version conflict, or reused `submission_id`/reply version with different content |
| `SUBMISSION_ID_EXPIRED` | 410 | No | A registered but unused `submission_id` passed its validity period. The customer must register a new one (C4a); the server never recreates it. |
| `RATE_LIMITED` | 429 | Yes | Per-customer limit reached |
| `INTERNAL_ERROR` | 500 | Yes | Unexpected failure, no details exposed |
| `SERVICE_BUSY` | 503 | Yes | Aggregate admission bound reached; includes `Retry-After` |
| `DEPENDENCY_UNAVAILABLE` | 503 | Yes | Storage or other required dependency down. For C4b this means **the save is known to have failed; nothing stored**. |
| `SAVE_OUTCOME_UNCERTAIN` | 503 | Yes | C4b only. The commit outcome is unknown ("confirmation unavailable"). The client must resolve it with the same `submission_id` (C4c or a same-content retry) and must not claim that nothing was saved. |
| `DEADLINE_EXCEEDED` | 504 | Yes | End-to-end deadline passed before any controlled outcome could be returned (see C1) |

### 2.6 Privacy and logging (all contracts)

Permitted log fields: `correlation_id`, normalized error category, duration, `configuration_version`, retry count. Not logged: question, answer, note, comment text, session identifiers, CSRF tokens, provider keys, raw provider errors, direct customer identifiers. General chat transcripts are **not persisted**. Diagnostic logs are kept 7 days (V33); inquiry metadata 30 days (V32); confirmed support content and replies while open plus 30 days after resolution (V11). *Open (David):* whether `subject_id` may be logged for audit.

### 2.7 Service target and overload (D11, planning basis 167 inquiries/s)

**Proposed service level (Vlad, awaiting capacity evidence):** at least 95% of **eligible** inquiries receive a supported AI answer within 15 seconds.
- *Eligible* means a valid, authorized, in-scope inquiry with supporting evidence, assigned `route: ai` before admission.
- Busy responses, timeouts, invalid answers and unnecessary fallbacks count as **misses** and stay in the denominator.
- Explicit human requests (`route: human_requested`) and genuinely unsupported questions are reported separately.
- Applies a 20 s end-to-end deadline (V4) and a provider timeout of at most 12 s (V6).

C1 therefore returns `route` and the server records the outcome status so David can compute the ratio. **Measurement:** from application receipt to the complete returned answer. Report offered, eligible, admitted, answered within target, answered late, fallback, rejected, failed and timed-out counts separately. A 200 fallback is not an AI answer. A second target, **95% of successful durable support saves within 2 s** (V31), is measured separately and never acknowledges before commit.

**Admission.**
- Per-customer limits (**one active inquiry per customer** and at most 5 per minute, V8) plus an aggregate AI-generation concurrency limit (V15, open). A second inquiry while one is active returns 429 `RATE_LIMITED`.
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
| V11 | Completed-receipt and support-content retention | Receipts: the retained request's lifetime. Support content and replies: while open plus 30 days after resolution. Unused-ID expiry never deletes a completed receipt. | Decisions log D09 (Draft 2: 24 h) | Closed (proposed); David to review purge, backup and audit retention |
| V12 | Feedback comment length | 0-500 chars | Short comments | Proposed |
| V13 | Agent queue page size | default 25, max 100 | Small responses | Proposed |
| V14 | Peak factor over 167 inquiries/s | not set | Needs Vlad and David | **Open** |
| V15 | Aggregate generation concurrency limit | not set | Depends on V14 and provider quota (Collins) | **Open** |
| V16 | AI queue size and queue-wait limit | **none**: no AI waiting queue | Vlad: bounded admission, immediate `SERVICE_BUSY` | Closed (proposed) |
| V17 | Provider retry budget | 0 automatic generation retries; no second-provider failover | D11 and D14 | Closed (proposed); Collins to confirm |
| V18 | Circuit breaker | Opens after **3 consecutive** qualifying provider failures (timeout, connection, service) within 60 s; a successful call resets the count; 30 s cooldown; then **one** shared recovery trial on a new admitted inquiry (20 s lease, per provider/model/credential scope); success closes, failure reopens. Failed inquiries are not resubmitted. 429 and quota-reset guidance is respected and an exhausted quota is not probed every 30 s. Configuration failures, customer validation failures, unsupported questions and semantic rejections do not count. State is shared through M9 with atomic version changes and no database lock held during the external call. | Decisions log D14 (Vlad's defaults) | Proposed; counter, reset and write policy **Open** (Collins; David reviews races) |
| V19 | Evidence-sufficiency rule (pre-generation) and runtime evidence-support rule (C10) | not set | Collins defines the executable rules; C10 defines where they plug in | **Open** (Collins) |
| V20 | Tenant model | One company initially; multi-company deferred | D07 | Closed (proposed); Vlad to confirm |
| V21 | Retention for feedback and requests | not set | Privacy decision | **Open** (David) |
| V22 | Customer-data allowlist | `customer_id`, `account_status` only | Vlad: initial case is read-only account status, deterministic, no AI | Proposed. Which inquiries need it remains **Open**. |
| V23 | Session idle expiry | 30 min | Typical for a support chat; limits stolen-session window | Proposed (Hanlin; Vlad and David to confirm) |
| V24 | Session absolute expiry | 8 h | Bounds a session regardless of activity | Proposed |
| V25 | Unused `submission_id` validity (escalation and reply IDs) | 30 min from registration; max 3 unused IDs outstanding per customer | Long enough to review and edit, short enough to bound stale IDs | Proposed (Hanlin); David asked to recommend |
| V26 | Feedback expiry | Feedback expires with its inquiry metadata (see V32). No separate submission window. | D05 and D09 | Closed (proposed); replaces Draft 3's 7-day window |
| V27 | Service level | 95% of eligible inquiries answered within 15 s | Vlad (D11) | Proposed; awaits capacity evidence |
| V28 | Fallback reserve before the 20 s deadline | 1 s | Leaves time to return a controlled 200 instead of 504 | Proposed; Collins to confirm |
| V29 | Customer reply deduplication | Registered `reply` ID per customer, parent request and operation; plus atomic state and `expected_version` check | D17 | Proposed; David to review conflict and recovery cases |
| V30 | Model token bounds | At most 4,096 total input tokens (instructions, question, evidence) and 512 output tokens; highest-ranked permitted passages that fit; eight maximum-size passages need not fit | D15; exact model dependent | Proposed; Collins to confirm against the model |
| V31 | Durable support save target | 95% of successful saves within 2 s | D11 | Proposed; David defines measurement |
| V32 | Inquiry metadata retention | 30 days from creation; linked feedback expires with it; scheduled daily cleanup | D09 | Proposed (Vlad); David reviews |
| V33 | Diagnostic log retention | 7 days, no raw question, answer or customer content, credentials or direct customer identifiers | D09 | Proposed (Vlad); David reviews |

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

**Examples (D18)**

`GET /v1/session` (the browser sends the session cookie automatically; values are fictional):
```
Cookie: session=<opaque; Secure; HttpOnly; SameSite=Lax>
```
```json
{
  "contract_version": "0.3.1",
  "role": "customer",
  "expires_at": "2026-11-01T23:00:00Z",
  "idle_expires_at": "2026-11-01T15:30:00Z",
  "csrf_token": "demo-csrf-token-value",
  "correlation_id": "4b5c6d7e-8f9a-4b0c-9d1e-2f3a4b5c6d7e"
}
```

State-changing request with the token:
```
POST /v1/inquiries
Cookie: session=<opaque>
X-CSRF-Token: demo-csrf-token-value
```

The same request without the token returns 403:
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "CSRF_FAILED",
    "message": "Your session could not be verified for this action. Please reload the page and try again.",
    "retryable": false,
    "correlation_id": "5c6d7e8f-9a0b-4c1d-8e2f-3a4b5c6d7e8f"
  }
}
```

**Tests:** forged `customer_id` or `role` in a body is ignored; customer session calling an agent endpoint returns 403; administrator session calling C4/C5/C6 content endpoints returns 403; expired (idle and absolute) session returns 401; `POST` without CSRF token returns 403 `CSRF_FAILED`; a session created on replica A is accepted on replica B; the session identifier changes at login; after logout the same cookie returns 401; the request built for C3 contains no `AccessContext` field.

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
  "contract_version": "0.3.1",
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
  "contract_version": "0.3.1",
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
  "contract_version": "0.3.1",
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
| Per-customer limit (5 per minute), or a second inquiry while one is active | 429 `RATE_LIMITED` + `Retry-After` |
| Aggregate admission bound or open circuit with no capacity to try | 503 `SERVICE_BUSY` + `Retry-After`. No queue; the browser keeps the question. |
| Insufficient, conflicting or stale evidence | 200 `clarification_requested` or `escalation_offered`, `suggested_reason: insufficient_evidence`; no unsupported answer shown |
| C10 validation fails (including the runtime evidence-support check) | 200 `clarification_requested` or `escalation_offered`, `suggested_reason: validation_failed`; candidate suppressed |
| Retrieval timeout or unavailable (C2a) | 200 `temporarily_unavailable`, `escalation_offered: true`, `suggested_reason: service_unavailable`. Not treated as proof that no source exists. |
| Provider failure (C3, any category including provider timeout and `circuit_open`) | 200 `temporarily_unavailable`, `escalation_offered: true`, `suggested_reason: provider_failure`; question preserved in the UI |
| Required customer context unavailable (C7) | 200 `escalation_offered`, `suggested_reason: service_unavailable` (controlled; no guessed customer facts) |
| Explicit human request recognized | 200 `escalation_offered`, `route: human_requested`, `suggested_reason: human_requested` |
| End-to-end 20 s deadline expires while a response can still be delivered | 504 `DEADLINE_EXCEEDED` |

**Provider timeout versus 504 (Collins's question).**
- A provider timeout is a C3 `timeout` failure at the provider limit (V6, at most 12 s). It returns **200 `temporarily_unavailable`** inside the 20 s budget.
- `InquiryService` stops waiting on any dependency at deadline minus the fallback reserve (V28) and returns the controlled 200 fallback if it can.
- **504 `DEADLINE_EXCEEDED` is returned when the overall 20 s deadline expires and a response can still be delivered (D04)**, for example a stalled non-provider dependency that never returned within the reserve. In normal operation the provider timeout fires first and the customer gets the controlled 200.
- A late provider result arriving after the fallback or 504 is discarded. It never replaces the response, never creates a support request, and never overwrites a newer inquiry in the browser (match results by `inquiry_id`).

*Closed with Collins's support (PR #17 review):* provider failure is 200 with a status; only admission overload is 503. Collins to confirm the 504 backstop wording and V28.

**Persistence.** The inquiry's minimal metadata (status, route, source refs, `configuration_version`) is stored before responding and kept 30 days (V32). No general chat transcript is persisted. Question text storage is subject to the retention decision (V21).
**Privacy.** The question goes to the provider through C3 only on the `ai` route; never logged. Account-status inquiries send nothing to the provider.

**Tests:** supported question returns `answered` with citations that resolve; unsupported returns `escalation_offered` with no answer; ambiguous returns `clarification_requested`; empty and oversized input return 400; no session returns 401; missing CSRF returns 403; other customer's conversation returns 403; provider timeout (mock) returns `temporarily_unavailable` in under 20 s; retrieval outage (mock) returns `service_unavailable`, not `insufficient_evidence`; 6th request in a minute returns 429; a second inquiry while one is active returns 429; saturated admission returns 503 `SERVICE_BUSY` immediately with no queued request; stalled dependency past the deadline returns 504 and a late provider result does not replace the response; account-status question makes zero provider calls; `route` is present on every 200.

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
- **No automatic generation retry** (V17 = 0) and no automatic failover to a second provider (deferred; B17 is consolidated into B11). A failed inquiry is never resubmitted automatically.
- **Token bounds (V30):** the adapter keeps total input within 4,096 tokens by selecting the highest-ranked permitted passages that fit, and caps output at 512 tokens. Oversized customer input is rejected at C1, not silently altered. Truncated or incomplete output is never presented as complete (`invalid_provider_response`).
- **Circuit breaker (V18, proposed; D14):** three **consecutive** qualifying failures within 60 s open the breaker; a successful call resets the count; cooldown 30 s; then one global recovery trial per provider/model/credential scope on a new admitted inquiry, guarded by a 20 s lease in shared storage (M9) with atomic state and version changes and no database lock held during the provider call. Stale trial results are ignored and expired leases recovered. If shared breaker or admission state cannot be obtained, the adapter does **not** launch unlimited calls; it returns `circuit_open` or a controlled unavailable outcome. 429 guidance and quota resets are respected, and an exhausted quota is not probed every 30 s. Configuration failures need correction and do not count as outages. The counter, reset and write policy is Collins's.
- Late results are discarded and never replace a completed fallback response or create a support request.
- Text in passages or customer input is data. Instructions inside it never override policy or grant tools or database access.
- Credentials stay server-side. Only the question and permitted passages are sent. Never customer database records, session data, tokens or `AccessContext`.

**Examples (D06)**

Allowed outbound payload (everything the adapter may send; no role, subject, session, customer field or credential):
```json
{
  "question": "How do I set up the Campus VPN profile?",
  "passages": [{
    "ref": { "source_id": "DOC-003", "section_id": "s2", "source_version": "3" },
    "text": "Install the Acme VPN client, sign in, and select the Campus profile.",
    "score": 0.91,
    "rank": 1
  }],
  "deadline_ms": 11000,
  "configuration_version": "cfg-0.1",
  "correlation_id": "6d7e8f9a-0b1c-4d2e-9f3a-4b5c6d7e8f9a"
}
```

Forged-context denial. A browser body that tries to set identity or scope is ignored, and the server uses the session:
```json
{ "question": "Show me my account", "customer_id": "CUST-009999", "role": "administrator" }
```
`InquiryService` builds `AccessContext` from the session (customer `CUST-004821`, role `customer`). `customer_id` and `role` in the body are discarded. The same body sent to an agent endpoint returns 403 `FORBIDDEN`. A `GenerationRequest` containing any extra field (for example `ctx` or `approved_context`) is rejected before the provider call.

**Tests:** valid input returns a candidate with `cited_refs`; each failure category maps correctly (mock); open breaker returns `circuit_open` without a provider call; with two replicas and an expired lease, exactly one half-open trial runs; a passage containing "ignore your rules" does not change behavior; a result arriving after the deadline is ignored; configuration error triggers an operator alert and a customer-safe message; a request carrying any field outside the schema above (including `approved_context` or `ctx`) is rejected before the provider call; no automatic retry occurs after a `timeout`; a success after two failures resets the breaker count; three non-consecutive failures do not open it; a 429 with quota-exhausted guidance does not trigger a probe every 30 s; the request stays within 4,096 input tokens.

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

**Design (D09, D17; Vlad's walkthrough B2-B6).** The server issues and registers each `submission_id` before use. The ID is bound to the authenticated customer and the intended operation (`escalation`, or `reply` for one parent request). Only a registered, unused, unexpired ID can create anything. Registration alone creates **no** human-visible support request. A submit saves the request and completes its receipt in **one transaction**, with a database uniqueness rule for concurrent retries. The receipt stores a result reference and a payload-comparison value, not another copy of the support text. Disabling the submit button is a usability measure only, never the mechanism.

**Browser behavior (D04, D09).** The browser keeps unsent text in the current view without promising it survives a page reload. It must **not** automatically replace a failed retry with a fresh ID. A deliberate new submission requires a newly issued ID and the customer's confirmation.

#### C4a. `POST /v1/escalations/submission-ids` (register an ID for a new request)

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `operation` | enum `escalation` | Yes | Binds the ID to this operation |

**Response 201**

| Field | Type | Notes |
|---|---|---|
| `submission_id` | Uuid | Server-issued |
| `operation` | string | Echoed |
| `registration_state` | RegistrationState | `unused` |
| `expires_at` | Timestamp | Registration time plus V25 |
| `correlation_id`, `contract_version` | | |

```json
{
  "contract_version": "0.3.1",
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "operation": "escalation",
  "registration_state": "unused",
  "expires_at": "2026-11-01T15:34:05Z",
  "correlation_id": "0c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f"
}
```

| Condition | Response |
|---|---|
| More than V25's outstanding unused IDs | 429 `RATE_LIMITED` |
| Escalation capacity bound | 503 `SERVICE_BUSY` |
| Storage down | 503 `DEPENDENCY_UNAVAILABLE` |

Cancel needs no endpoint: an unused ID simply expires. Unused-ID expiry never deletes a completed receipt (V11).

#### C4b. `POST /v1/escalations` (submit)

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `submission_id` | Uuid | Yes | No | A registered ID owned by the caller and bound to `escalation` |
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
| `state` | RequestState | `queued` on first creation. On replay, the request's current state. |
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
  "contract_version": "0.3.1",
  "request_id": "f6a7b8c9-5555-4e66-8f77-3a88b99cc0dd",
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "state": "queued",
  "created_at": "2026-11-01T15:04:05Z",
  "acknowledgement": "Your request has been saved. It has not been read by an agent yet.",
  "correlation_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
}
```

**Example: same ID and same payload retried after a lost acknowledgment.** Returns **200** with the same body as above (same `request_id`, no second row).

**Example: same ID, changed content**
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "CONFLICT",
    "message": "This request was already sent with different text. To send something new, start a new request.",
    "retryable": false,
    "correlation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f"
  }
}
```

**Example: expired unused ID**
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "SUBMISSION_ID_EXPIRED",
    "message": "This form timed out before it was sent. Your text is still here; please send it again.",
    "retryable": false,
    "correlation_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
  }
}
```

**Example: commit outcome unknown**
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "SAVE_OUTCOME_UNCERTAIN",
    "message": "We could not confirm whether your request was saved. Please check its status before sending it again.",
    "retryable": true,
    "correlation_id": "4d5e6f7a-8b9c-4d0e-9f1a-2b3c4d5e6f7a"
  }
}
```

**Submit decision table (D09; Vlad's B3, B4, B6)**

| Situation | Behavior |
|---|---|
| Registered, unused, unexpired, owned by caller, valid payload | In **one transaction**: create the support request and the completed receipt under the unique key `(customer_scope [or tenant + customer], operation, submission_id)`. Returns 201. |
| Same ID, completed receipt, **same** payload comparison value | 200 with the original `request_id`; nothing new is created |
| Same ID, completed receipt, **different** content | 409 `CONFLICT` |
| Unused ID past its validity (V25) | 410 `SUBMISSION_ID_EXPIRED`. Never recreated or silently replaced. The UI keeps the text, offers C4c status checking and a deliberate new submission (a new C4a ID). |
| Unknown ID, missing registration or receipt, another customer's ID, or an ID bound to another operation | 404 `NOT_FOUND` (identical response; no cross-customer receipt lookup). After a retained request and receipt are purged, the old ID is unknown and cannot create anything. |
| 20 concurrent submits with the same ID | One transaction commits (unique constraint). The rest replay with 200. Exactly one row. |
| Validation fails | 400 `VALIDATION_FAILED` with field names; UI keeps content; no receipt claimed |
| Save **known** to have failed | 503 `DEPENDENCY_UNAVAILABLE` ("not saved"); nothing stored; retry with the **same** ID while unexpired |
| Commit outcome **uncertain** | 503 `SAVE_OUTCOME_UNCERTAIN` ("confirmation unavailable"); resolve with C4c or a same-ID, same-payload retry. The server never says that no record exists. |
| `consent_to_share` is false | 400 `VALIDATION_FAILED` |
| `inquiry_id` not caller's | 403 `FORBIDDEN` |
| Per-customer submit limit (V9) | 429 `RATE_LIMITED` |
| Escalation capacity bound | 503 `SERVICE_BUSY` (separate from generation capacity) |
| A provider result arrives late for the originating inquiry | No effect. A support request is never created automatically. |

**Payload comparison.** The receipt stores a hash of the canonical payload (`reason`, `inquiry_id`, `content`, `note`, `consent_to_share`). The receipt is created in the same transaction as the request.
**Persistence.** The stored request is the source of truth. If a queue broker is used, a transactional outbox (or equivalent) prevents loss between commit and publish. A C7 outage never blocks escalation: the request is saved with the `customer_id` from trusted context and enriched later. Completed receipts are kept for the retained request's lifetime (V11).
**Stored fields:** reviewed content, customer reference (from the trusted context), reason, originating inquiry reference, `submission_id`, payload hash, timestamps, `state`, `version`, assigned agent.
**Privacy.** Content and note are not logged and are not sent to the AI provider.
**Service target (D11):** 95% of successful durable saves complete within 2 s (V31). No acknowledgement is sent before commit.

#### C4c. `GET /v1/escalations/{submission_id}` (status, for reconciliation)

Customer, own records only. Works for both `escalation` and `reply` IDs.

| Field | Type | Notes |
|---|---|---|
| `submission_id` | Uuid | |
| `operation` | string | `escalation` or `reply` |
| `registration_state` | RegistrationState | `unused`, `completed` or `expired` |
| `saved` | boolean | True only when a completed receipt exists |
| `request_id` | Uuid | Null for an unused or expired escalation ID. For a reply ID, the parent request. |
| `state` | RequestState | Null unless `saved` |
| `created_at` | Timestamp | Null unless `saved` |
| `expires_at` | Timestamp | Null when `completed` |

Unknown ID or another customer's ID: 404 `NOT_FOUND`.

```json
{
  "contract_version": "0.3.1",
  "submission_id": "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc",
  "operation": "escalation",
  "registration_state": "completed",
  "saved": true,
  "request_id": "f6a7b8c9-5555-4e66-8f77-3a88b99cc0dd",
  "state": "queued",
  "created_at": "2026-11-01T15:04:05Z",
  "expires_at": null,
  "correlation_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b"
}
```

#### C4d. `POST /v1/escalations/{request_id}/reply-ids` (register an ID for a customer reply)

Customer, own request only. Same shape as C4a with `operation: "reply"`. The ID is bound to the customer, the parent `request_id` and the reply operation.

| Condition | Response |
|---|---|
| Request is `waiting_for_customer` | 201 with `submission_id`, `operation: "reply"`, `request_id`, `registration_state: "unused"`, `expires_at` |
| Request in any other state (including `resolved`) | 409 `CONFLICT` |
| Not the caller's request | 404 `NOT_FOUND` |

#### C4e. `POST /v1/escalations/{request_id}/replies` (submit a customer reply)

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `submission_id` | Uuid | Yes | A registered, unused, unexpired `reply` ID for this customer and this `request_id` |
| `message` | string | Yes | 1-2,000 chars. Text only; no attachments. |
| `expected_version` | int | Yes | The request `version` the customer last saw |

| Situation | Response |
|---|---|
| Valid ID, request is `waiting_for_customer`, `expected_version` matches | 201. In **one transaction**: save the reply, complete its receipt, move the request to `in_review`, **retain the assigned agent**, increment `version`. |
| Completed receipt, same payload | 200 with the original reply; no second message, no state change |
| Completed receipt, changed payload | 409 `CONFLICT` |
| Missing registration, or unused ID past its validity | Unknown or foreign ID: 404 `NOT_FOUND`. Expired unused ID: 410 `SUBMISSION_ID_EXPIRED`. |
| Request is `resolved` (late reply, or reply racing resolution) | 409 `CONFLICT`. The request is **not** revived. Resolved is terminal; the customer starts a new request through C4a. |
| Request in another state, or stale `expected_version` | 409 `CONFLICT` |
| Commit outcome unknown | 503 `SAVE_OUTCOME_UNCERTAIN`; check C4c or retry with the same ID and payload |
| Save known to have failed | 503 `DEPENDENCY_UNAVAILABLE` |

The ownership, state and version checks happen atomically with the save. Reply receipts are kept for the retained record's lifetime. Attachments, live chat, notification email and reopening are excluded in this draft. Customers return to the application for updates.

**Example reply request and 201 response**
```json
{
  "submission_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
  "message": "Reinstalling did not help. I am on the Campus network.",
  "expected_version": 4
}
```
```json
{
  "contract_version": "0.3.1",
  "reply_id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
  "request_id": "f6a7b8c9-5555-4e66-8f77-3a88b99cc0dd",
  "state": "in_review",
  "version": 5,
  "correlation_id": "8b9c0d1e-2f3a-4b4c-9d5e-6f7a8b9c0d1e"
}
```

**Example: late reply on a resolved request**
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "CONFLICT",
    "message": "This request has been resolved. Please start a new request.",
    "retryable": false,
    "correlation_id": "9c0d1e2f-3a4b-4c5d-8e6f-7a8b9c0d1e2f"
  }
}
```

**Tests (C4):** register returns an unused ID with `expires_at`; fourth outstanding unused ID returns 429; first submit returns 201 and one row plus one receipt; same-ID, same-payload retry returns 200 with one row; 20 concurrent same-ID submits create exactly one row; same ID with different content returns 409; unused ID after V25 returns 410, creates no row, and is not usable later; unknown ID and another customer's ID return identical 404; ID of a purged request is unusable; save failure (mock) returns 503 `DEPENDENCY_UNAVAILABLE`, no row, and the same-ID retry succeeds; commit-then-timeout (mock) returns `SAVE_OUTCOME_UNCERTAIN` and C4c then returns `saved: true`; `consent_to_share: false` returns 400; another customer's `inquiry_id` returns 403; administrator calling C4 returns 403; reply-ID registration on a non-waiting request returns 409; reply returns 201 and the request returns to `in_review` with the same agent; duplicate reply returns 200 with one stored message; reply racing resolution returns 409 and the request stays `resolved`; stale `expected_version` returns 409; replica B accepts a retry for an ID registered on replica A; an unused ID's expiry does not delete a completed receipt.

---

### C5. Agent review and update

**Owner:** `AgentQueueService` (M6). **Authorization:** `agent` only. Customers and administrators get 403. All `POST` endpoints require CSRF.

**Scope (D07).** One company initially. An agent sees the **unassigned queue** and the requests **assigned to that agent**, and nothing else. Another agent's request returns 404 `NOT_FOUND`.

**C5a. `GET /v1/agent/escalations?state=queued&limit=25&cursor=...`**
`state` is optional (`queued`, or a state of the caller's own assigned requests). `limit` 1-100, default 25. Returns `{ items: [EscalationSummary], next_cursor|null, correlation_id, contract_version }` with `EscalationSummary { request_id, state, content, reason, created_at, assigned_agent_id|null, customer_ref, account_status|null, version }`. Customer data is limited to the C7 allowlist (`customer_id`, `account_status`). `account_status` is null when C7 is unavailable.

**C5b. `POST /v1/agent/escalations/{request_id}/claim`**
No body. Atomic: succeeds only if `state = queued`; sets `assigned`, `assigned_agent_id = caller`, increments `version`, and returns the updated summary. If another agent claimed first, 409 `CONFLICT`.

```json
{
  "contract_version": "0.3.1",
  "request_id": "f6a7b8c9-5555-4e66-8f77-3a88b99cc0dd",
  "state": "assigned",
  "assigned_agent_id": "AGT-0007",
  "version": 2,
  "correlation_id": "0d1e2f3a-4b5c-4d6e-9f7a-8b9c0d1e2f3a"
}
```

**C5c. `POST /v1/agent/escalations/{request_id}/transition`**

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `to_state` | RequestState | Yes | Must be allowed below |
| `expected_version` | int | Yes | Optimistic check; mismatch returns 409 |
| `message_to_customer` | string | Cond. | Required for `waiting_for_customer`; 1-2,000 chars |
| `resolution_note` | string | Cond. | Required for `resolved`; 1-2,000 chars |
| `release_reason` | string | Cond. | Required for `queued` (release); 1-500 chars |

**Permitted transitions (proposed; D12, Hanlin and David to review)**

| From | To | Who | Extra field |
|---|---|---|---|
| `queued` | `assigned` | Any agent (via claim) | |
| `assigned` | `in_review` | Assigned agent | |
| `in_review` | `waiting_for_customer` | Assigned agent | `message_to_customer` |
| `waiting_for_customer` | `in_review` | System (customer reply, C4e), owner retained; or the assigned agent | |
| `in_review` | `resolved` | Assigned agent | `resolution_note` |
| `assigned`, `in_review` or `waiting_for_customer` | `queued` (release) | Assigned agent. Ownership is cleared. | `release_reason` |
| `resolved` | none | Terminal; late customer replies do not reopen it | |

Releasing from `in_review` or `waiting_for_customer` extends Hanlin's earlier rule and needs team agreement (D12). No direct takeover, auto-dispatch, supervisor or reopen workflow in this draft. Any other transition, a non-owner update, or a stale version returns 409 `CONFLICT`. Conflicting updates never silently overwrite each other (atomic owner and version check).

| Other conditions | Response |
|---|---|
| Not an agent | 403 `FORBIDDEN` |
| Missing CSRF token | 403 `CSRF_FAILED` |
| Unknown `request_id`, or another agent's assigned request | 404 `NOT_FOUND` |
| Missing conditional field | 400 `VALIDATION_FAILED` |
| Storage down | 503 `DEPENDENCY_UNAVAILABLE` |

**Examples**

Transition request (to `waiting_for_customer`):
```json
{
  "to_state": "waiting_for_customer",
  "expected_version": 3,
  "message_to_customer": "Which network are you connecting from?"
}
```

Stale version, non-owner and second claim all return the same envelope shape:
```json
{
  "contract_version": "0.3.1",
  "error": {
    "code": "CONFLICT",
    "message": "This request was changed by someone else. Reload it and try again.",
    "retryable": false,
    "correlation_id": "1e2f3a4b-5c6d-4e7f-8a8b-9c0d1e2f3a4b"
  }
}
```

**Audit.** Each transition records agent ID, old and new state, `correlation_id`, and timestamp, not content. A release records that a reason was given, not its text.

**Tests:** customer or administrator on any C5 endpoint returns 403; two concurrent claims give one 200 and one 409; non-owner transition returns 409; another agent's assigned request returns 404; `resolved` then any transition returns 409; stale version returns 409; `waiting_for_customer` without a message returns 400; release from each of the three owned states without `release_reason` returns 400, and with it returns the request to `queued` with no owner so a second agent can claim it; customer reply moves the request back to `in_review` with the same owner; saved request visible in queue after a simulated broker failure; C7 outage still lists requests with `account_status: null`.

---

### C6. Feedback and reviewed improvement

**Owner:** `FeedbackService` (M8). Learning is a **reviewed** loop. Feedback is evidence, not an instruction to the model and not an automatic training signal.

**C6a. `POST /v1/feedback`** (customer, CSRF required)

**Design (D05).** Feedback needs an inquiry, a rating and an optional comment. It does **not** require an answer ID. The server verifies inquiry ownership and derives the outcome, `route` and `configuration_version` from trusted inquiry metadata. If the inquiry produced an answer, the server keeps a nullable internal link to it.

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `inquiry_id` | Uuid | Yes | No | Must belong to caller |
| `rating` | enum `helpful`, `not_helpful` | Yes | No | |
| `category` | enum `incorrect`, `incomplete`, `wrong_source`, `unclear`, `too_much_escalation`, `fallback_unhelpful`, `other` | No | Yes | Only with `not_helpful`, and only if valid for the recorded outcome: `incorrect`, `incomplete`, `wrong_source` need an `answered` outcome; `too_much_escalation`, `fallback_unhelpful` need a non-answered outcome; `unclear`, `other` fit any |
| `comment` | string | No | Yes | 0-500 chars |

Response 201: `{ feedback_id, state: "pending_review", correlation_id, contract_version }`. Draft 3's client-supplied `answer_id` is removed.

**Expiry (D05, D09, V32).** Inquiry metadata is kept 30 days from creation, and linked feedback expires with it. Feedback for an inquiry whose metadata has been purged returns 404 `NOT_FOUND`. There is no separate submission window.

**Examples**

Feedback on an answered inquiry:
```json
{
  "inquiry_id": "b1d2c3e4-1111-4a22-8b33-9c44d55e6f77",
  "rating": "not_helpful",
  "category": "wrong_source",
  "comment": "The guide I opened was for a different VPN."
}
```

Feedback on a failed inquiry (no answer exists):
```json
{
  "inquiry_id": "c2e3d4f5-2222-4b33-9c44-0d55e66f7788",
  "rating": "not_helpful",
  "category": "fallback_unhelpful",
  "comment": "I only needed the VPN steps."
}
```

201 response for either:
```json
{
  "contract_version": "0.3.1",
  "feedback_id": "2f3a4b5c-6d7e-4f8a-9b9c-0d1e2f3a4b5c",
  "state": "pending_review",
  "correlation_id": "3a4b5c6d-7e8f-4a9b-8c0d-1e2f3a4b5c6d"
}
```

**C6b. `GET /v1/agent/feedback?state=pending_review&limit=25`** (agent with reviewer permission) lists feedback with outcome, route, source and configuration versions.

**C6c. Improvement proposals** (agent with reviewer permission; all `POST` require CSRF)

| Endpoint | Purpose |
|---|---|
| `POST /v1/agent/improvements` | Propose a bounded change: `{ type: "knowledge_source"\|"retrieval"\|"prompt"\|"configuration", description (1-2,000), linked_feedback_ids (1-50) }` |
| `POST /v1/agent/improvements/{id}/review` | A **different qualified member** approves or rejects, and records privacy-impact notes: `{ decision: "approve_for_evaluation"\|"reject", privacy_note (1-1,000) }`. Reviewer must differ from the proposer (else 409 `CONFLICT`). |
| `POST /v1/agent/improvements/{id}/evaluation` | Record the result against the fixed baseline: `{ baseline_id, report_ref, passed: boolean }` |
| `POST /v1/agent/improvements/{id}/release` | Allowed only if evaluation passed. Requires `rollback_ref`. Creates a new `configuration_version`. Release authorization is coordinated by Vlad (D08). |
| `POST /v1/agent/improvements/{id}/rollback` | Restores the prior version; records reason |

**How a release takes effect (Vlad's M8).** Approved source changes enter through M3 using the C8 boundary. Approved generation or prompt configuration is applied through M4. The existing review workflow is used, not a separate approval application. No automatic retraining or release from ratings.

**Proposal states:** `proposed`, `approved_for_evaluation`, `evaluated`, `released`, `rejected`, `rolled_back`. Skipping a state returns 409 `CONFLICT`.

**One complete improvement and rollback example (D08).**
```text
// 1. propose
POST /v1/agent/improvements
{ "type": "knowledge_source",
  "description": "Add a Campus VPN profile section to DOC-003.",
  "linked_feedback_ids": ["2f3a4b5c-6d7e-4f8a-9b9c-0d1e2f3a4b5c"] }
-> 201 { "id": "imp-001", "state": "proposed" }

// 2. independent review (different person)
POST /v1/agent/improvements/imp-001/review
{ "decision": "approve_for_evaluation", "privacy_note": "No customer text copied into the document." }
-> 200 { "id": "imp-001", "state": "approved_for_evaluation" }

// 3. evaluation against the fixed baseline
POST /v1/agent/improvements/imp-001/evaluation
{ "baseline_id": "base-b12-v1", "report_ref": "eval-2026-11-02", "passed": true }
-> 200 { "id": "imp-001", "state": "evaluated" }

// 4. release with a rollback reference
POST /v1/agent/improvements/imp-001/release
{ "rollback_ref": "cfg-0.1" }
-> 200 { "id": "imp-001", "state": "released", "configuration_version": "cfg-0.2" }

// 5. rollback
POST /v1/agent/improvements/imp-001/rollback
{ "reason": "Answers cited the new section incorrectly." }
-> 200 { "id": "imp-001", "state": "rolled_back", "configuration_version": "cfg-0.1" }
```
(Annotations show intent; real requests are plain JSON.)

| Condition | Response |
|---|---|
| Invalid enum, `category` with `helpful`, category not valid for the outcome, comment too long | 400 `VALIDATION_FAILED` |
| Inquiry not the caller's | 403 `FORBIDDEN` |
| Inquiry unknown or its metadata purged | 404 `NOT_FOUND` |
| Duplicate feedback for the same inquiry | 409 `CONFLICT` |
| Customer or administrator on agent endpoints | 403 `FORBIDDEN` |
| Release without a passed evaluation or `rollback_ref` | 409 `CONFLICT` |

**Privacy.** Comments are visible only to authorized reviewers. Aggregates minimize identifiers. Raw feedback is not placed in the public repository. Linked feedback expires with its inquiry metadata (30 days); other retention is open (V21). Comments are not logged and not sent to the provider.
*Open (Vlad):* exactly which role authorizes a release. This draft assumes agents with reviewer permission propose and review, Vlad coordinates release authorization (D08), and administrators do not see feedback content.

**Tests:** feedback on an answered inquiry returns 201 with outcome and versions stored; feedback on a fallback inquiry with no answer returns 201; `wrong_source` on a non-answered inquiry returns 400; `fallback_unhelpful` on an answered inquiry returns 400; duplicate returns 409; feedback on a purged inquiry returns 404 and linked feedback is deleted with the inquiry; the same person proposing and reviewing returns 409; release without evaluation returns 409; harmful proposal fails evaluation and cannot be released; rollback restores the prior `configuration_version`; administrator reading feedback returns 403.

---

### C7. Existing customer database

**Owner:** `CustomerDirectoryAdapter` (M7). Read-only in this draft. No real system is connected; the adapter is specified against a fictional "CustomerDB". The AI provider has no direct database connection and never receives customer-database fields. Account changes go to a human.
**Method:** `get_customer_profile(ctx: AccessContext, customer_id: str, deadline_ms: int) -> CustomerProfile`
**Callers:** `InquiryService` (account-status operation), `EscalationService` and `AgentQueueService` (enrichment). The `customer_id` must equal `ctx.customer_scope` for a customer; agents may look up the customer of a request they hold.

| Input | Constraints |
|---|---|
| `customer_id` | `^CUST-[0-9]{6}$`, e.g. `CUST-004821` |
| `deadline_ms` | 1-2000 |

**`CustomerProfile` (allowlist, V22):** `customer_id`, `account_status` (`active`, `suspended`). Excluded: display name, tier, email, phone, address, payment and credential data (D16). Adding a field requires a team decision.

| Condition | Behavior |
|---|---|
| Bad ID format | `InvalidCustomerId` (400) |
| ID outside caller's scope | `AccessDenied` (403) |
| Not found | `CustomerNotFound` (404) |
| Timeout or database down | `CustomerDirectoryUnavailable` |

**Examples (fictional data)**

Authorized lookup (customer `CUST-004821` asking about their own account):
```json
{ "call": "get_customer_profile(ctx{role: customer, customer_scope: CUST-004821}, 'CUST-004821', 2000)",
  "result": { "customer_id": "CUST-004821", "account_status": "active" } }
```
C1 then answers from a fixed template: "Your account is currently active." No model call.

Denied lookup (the same customer asks for another ID):
```json
{ "call": "get_customer_profile(ctx{role: customer, customer_scope: CUST-004821}, 'CUST-009999', 2000)",
  "result": "AccessDenied (403)" }
```
Nothing about `CUST-009999` is disclosed, and C1 does not reveal whether that ID exists.

Unavailable lookup:
```json
{ "call": "get_customer_profile(ctx{...}, 'CUST-004821', 2000)",
  "result": "CustomerDirectoryUnavailable" }
```
C1 returns 200 `escalation_offered` with `suggested_reason: service_unavailable` and states no customer fact. Escalation still saves.

**Failure handling**
- Account-status inquiries return a **deterministic** answer from `account_status` using fixed templates, with no model generation. Required context that is unavailable is explained without guessing, and support is offered.
- General questions need no lookup and proceed without it.
- `EscalationService` always saves the request using the `customer_id` from trusted context, and enriches it later. A C7 outage never blocks confirmed request saving.
- Optional cache (proposed, open): keyed by customer and scope, short-lived, and invalidated on access change.
- *Open (Vlad):* whether any update operation is ever permitted. Draft assumes none.
- *Open (team):* D16 describes an "explicit account-status operation". This draft routes it through C1 using `route: account_status`. If the team prefers a separate endpoint, C1 loses that route.

**Tests:** valid ID returns only `customer_id` and `account_status`; ID outside scope is denied and discloses nothing; not found raises `CustomerNotFound`; timeout (mock) raises `CustomerDirectoryUnavailable`, escalation still saves, and an account-status inquiry returns the controlled escalation offer; the C3 request never contains customer-database fields; an account-status inquiry produces no provider call.

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
| Agent scope (unassigned queue plus own assignments only) | C5 |
| Session expiry, login rotation, logout, replica sharing, CSRF | C9 and every state-changing endpoint |
| Invalid, stale or unsupported citations | C2, C10 |
| Provider failure, late results, config errors | C1, C3 |
| Circuit breaker concurrency across replicas, stale trial results | C3 |
| Duplicate, expired, unknown, purged or lost submission ID | C4 |
| Uncertain commit versus known failed save | C4 |
| Duplicate, late or resolution-racing customer replies | C4e |
| Concurrent claim, stale updates, release from each owned state | C5 |
| Malicious feedback or prompt injection | C3, C6 |
| Feedback with no answer; feedback expiry with inquiry metadata | C6 |
| Overload, bounded admission, no AI queue, one active inquiry | C1, C3, C4 |
| Service level (95% within 15 s, denominator-aware) and durable save (95% within 2 s) | C1, C4 |
| Required customer data unavailable | C1, C7 |
| Customer data and `AccessContext` never reach the provider | C3, C7, C9 |
| Token and payload bounds | C1, C3, C4 |

---

## 6. Changes

### 6.1 Draft 3 to Draft 3.1 (this revision)

Source: Vlad's decisions log (D01-D21, revision 4). PR #16 and PR #18 were opened, but only their descriptions were readable. Collins's flow file and David's verification files did not load, so nothing here depends on their contents.

| Draft 3 | Draft 3.1 |
|---|---|
| Feedback window of 7 days with `FEEDBACK_WINDOW_CLOSED` (V26) | Feedback expires with inquiry metadata (30 days, D05/D09). No separate window or error code. Late feedback on a purged inquiry is 404. |
| C6 request carried an optional `answer_id` | Removed. The server derives outcome, route and configuration from trusted metadata and links an answer internally if one exists. Category must be valid for the recorded outcome. |
| Customer replies deduplicated by `expected_version` only | D17: replies use server-issued, registered `reply` IDs scoped to customer, parent request and operation. New C4d (register) and C4e (submit). Receipt saved in the same transaction. A reply racing resolution cannot revive the request. |
| `waiting_customer` | `waiting_for_customer`, following D12/D17, Collins's model and Draft 2. Vlad's architecture review still says `waiting_customer`; Vlad to reconcile. |
| Release only from `assigned` | Owner may release from `assigned`, `in_review` or `waiting_for_customer`, with a reason. A customer reply keeps the owner. |
| Agents listed requests by state | D07: unassigned queue plus requests assigned to the caller. Others return 404. |
| Breaker: three failures within 60 s | D14: three **consecutive** qualifying failures within 60 s; a success resets the count; recovery uses one shared trial on a new admitted inquiry; failed inquiries are not resubmitted; exhausted quota is not probed every 30 s; configuration failures do not count. |
| No one-active-inquiry rule | D11: one active inquiry per customer (plus the 5-per-minute limit) |
| No durable-save target | D11: 95% of successful durable saves within 2 s (V31) |
| No token bounds | D15: at most 4,096 input and 512 output tokens (proposed, model-dependent) (V30) |
| Retention partly implied | D09: inquiry metadata 30 days, diagnostic logs 7 days, no general chat transcripts, confirmed support content while open plus 30 days after resolution (V32, V33) |
| Tenant model open | D07: one company initially; multi-company deferred. V20 closed (proposed). |
| 504 described only as a backstop | D04: 504 when the overall 20 s deadline expires and a response can still be delivered. Provider timeout (at most 12 s) is a controlled 200. |
| Missing examples | Added: C3 allowed outbound payload and forged-context denial (D06); cookie and CSRF (D18); C4 changed-payload, uncertain-commit and status examples (D09/D17); reply, late-reply and conflict examples (D12/D17); agent claim, transition and conflict examples (D12); C7 authorized, denied and unavailable (D02/D16); one complete improvement and rollback (D08); feedback on an answered and a failed inquiry (D05). |
| Contract inventory C4a-C4d | C4a register, C4b submit, C4c status, C4d register reply ID, C4e submit reply |

### 6.2 Draft 2 to Draft 3 (kept for history; superseded where 6.1 says so)

| Draft 2 | Draft 3 |
|---|---|
| `submission_id` generated by the browser | Server-issued and pre-registered via new C4a; bound to customer and operation; expiry V25 |
| C4a submit, C4b status, C4c reply | Renumbered: C4a register, C4b submit, C4c status, C4d reply |
| Reused ID with unknown or expired state undefined | 410 `SUBMISSION_ID_EXPIRED` (never recreated); unknown or foreign ID is 404; uncertain commit is 503 `SAVE_OUTCOME_UNCERTAIN` |
| 24 h idempotency retention (V11, open) | Receipt retained for request lifetime plus 30 days after resolution |
| Customer reply allowed only in `waiting_for_customer` | Renamed `waiting_for_customer`; replies carry `expected_version`; duplicate reply replays; late reply on `resolved` returns 409 |
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
| `contract_version` `"0.2"` | `"0.3.1"` |

---

---

## 7. Open decisions

1. **Vlad:** identity provisioning and whether an all-sessions logout exists (D18); peak factor and generation concurrency (V14, V15); whether C7 is strictly read-only; the exact role that authorizes releases (D08); reconcile `waiting_customer` (architecture review) with `waiting_for_customer` (decisions log, D12/D17); confirm single-company scope (V20).
2. **Collins:** confirm the 504 wording and fallback reserve (V28); breaker counter, reset and write policy, and which failures qualify (V18, D14); the runtime evidence-support rule and the pre-generation sufficiency rule (V19, D03); confirm zero retries (V17); provider and model quota evidence (D13).
3. **David:** recommend session idle and absolute lifetimes, unused-ID expiry (V23-V25), and whether an all-sessions logout is needed (D18); review receipt, purge, backup and audit retention (V11, V21, V32, V33); review the transition table, release rule, and reply registration; review the eligible-inquiry denominator and the breaker race cases.
4. **Team:** which inquiries use `account_status` and how `route` is decided (D16 says "explicit account-status operation"); confirm all proposed values; record decisions in `decisions.md`.
5. **Diagram:** component names, the C4a-C4e sub-contracts, and the C8-C10 interactions must appear exactly as named here, including the session store, receipt store and breaker state held through M9.

**Not verified in this draft:** David's session and unused-ID recommendations and Collins's evidence and breaker policy details. The log says they are still requested. V23, V24, V25 and V19 are placeholders until they respond.

## 8. Contribution note

## Hanlin Wang

**Role:** Lead for interface contracts (C1-C10).

**What I did**
- Drafted the interface contracts, including shared conventions, error codes, and the proposed-values table (Drafts 1 and 2).
- Revised the contracts after reading Vlad's Nov 1 architecture review, the decisions log, issue #12, and Collins's review on PR #17 (Drafts 3 and 3.1, proposed and pending review):
  - D09/D17: server-issued, pre-registered submission IDs for escalations and replies, scoped receipts, atomic saving, same and changed-payload retries, expired and missing IDs, and duplicate replies (C4a-C4e).
  - D05/D12/D18: feedback without an answer and its expiry with inquiry metadata (C6), agent scope, conflicts, release and late replies (C4e, C5), and session, login rotation, logout and CSRF behavior (C9b). Session lifetimes are my proposals; David's recommendations are not yet incorporated.
  - D11: aligned C1-C10 with the proposed service target, one-active-inquiry rule, 2-second save target, the `route` field, and Collins's failure rules; the evidence-support rule itself remains Collins's.
- Addressed Collins's three review points on PR #17 and the provider-timeout versus 504 question.
- Listed open decisions for Vlad, Collins, and David in Section 7.

**Reviews**
- Requested review from Collins (interfaces) and David (verification). Vlad checks architecture consistency.
- Draft 3.1 has not yet been reviewed. Collins's comments on Draft 2 are addressed and need his confirmation.

**Tools used**
- I used an AI assistant (Claude) to help draft and structure the contracts. I reviewed the content and checked it against the team documents.

**Not yet done / limits**
- All limits are proposals pending team approval.
- No implementation or testing has been done. This is a design specification.
