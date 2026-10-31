# DeskGuide Interface Contracts (Draft 1)

**Lead:** Hanlin | **Reviewers:** Collins (interfaces), David (verification) | **Coordinate names with:** Vlad
**Status:** First draft. All limits are *proposed*, not team-approved (see Section 3). Component and status names must be matched to Vlad's diagram and Collins's AI flows before the final version.
**Data:** All examples are fictional.

---

## 1. Contract inventory

| ID | Interaction | Component (owner module) | Caller to Callee | Interface |
|---|---|---|---|---|
| C1 | Customer inquiry and answer | `InquiryService` | Web UI to API | `POST /v1/inquiries` |
| C2 | Retrieval / source access | `Retriever` | `InquiryService` to `Retriever`; UI to API | `retrieve()`; `GET /v1/sources/{source_id}` |
| C3 | AI generation adapter | `GenerationAdapter` | `InquiryService` to adapter to external AI provider | `generate()` |
| C4 | Human escalation | `EscalationService` | Web UI to API | `POST /v1/escalations` |
| C5 | Agent review / update | `AgentQueueService` | Agent UI to API | `GET /v1/agent/escalations`, `POST .../{id}/claim`, `POST .../{id}/transition` |
| C6 | Feedback / improvement | `FeedbackService` | Web UI and Agent UI to API | `POST /v1/feedback`, `GET /v1/agent/feedback`, `POST /v1/agent/feedback/{id}/review` |
| C7 | Existing customer database | `CustomerDirectoryAdapter` | `InquiryService`, `EscalationService` to adapter to customer DB | `get_customer_profile()` |

**Roles:** `customer`, `agent`. The prototype's "employee" maps to `customer` and "administrator" maps to `agent`. *(Confirm with Vlad.)*

---

## 2. Shared conventions (apply to every contract)

**Versioning.** The path prefix `/v1/` is used for HTTP. Every response body includes `contract_version: "1.0"`. Breaking changes mean `/v2/`.

**Headers.**

| Header | Direction | Rule |
|---|---|---|
| `Authorization: Bearer <token>` | Request | Required on all endpoints. Token carries `subject_id` and `role`. |
| `X-Correlation-ID` | Request, Response | Optional on request (UUID v4). The server generates one if absent and always echoes it. It appears in every log line. |
| `Idempotency-Key` | Request | Required on `POST /v1/escalations`. UUID v4. |
| `Retry-After` | Response | Seconds. Sent on 429 and 503. |

**Error envelope (all non-2xx responses).**

```json
{
  "contract_version": "1.0",
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Your question must be between 1 and 1000 characters.",
    "retryable": false,
    "correlation_id": "6f1c2a9e-3b7d-4d0a-9c11-2f5e8a7b1d42",
    "details": [{"field": "question", "rule": "length_1_1000"}]
  }
}
```

`message` is a safe, user-facing string and never contains stack traces, provider names, SQL, or credentials. `details` is present only for `VALIDATION_FAILED` and contains field names only, never echoed values.

**Stable error codes.**

| Code | HTTP | Retryable | Meaning |
|---|---|---|---|
| `VALIDATION_FAILED` | 400 | No | Malformed or out-of-range input |
| `UNAUTHENTICATED` | 401 | No | Missing, invalid, or expired token |
| `FORBIDDEN` | 403 | No | Role or scope not permitted |
| `NOT_FOUND` | 404 | No | Resource missing (or out of scope; see C2) |
| `CONFLICT` | 409 | No | Illegal state transition or ownership conflict |
| `IDEMPOTENCY_MISMATCH` | 422 | No | Same `Idempotency-Key` with a different body |
| `RATE_LIMITED` | 429 | Yes | Per-customer or global limit hit |
| `INTERNAL_ERROR` | 500 | Yes | Unexpected failure; no details exposed |
| `DEPENDENCY_UNAVAILABLE` | 503 | Yes | AI provider, retriever, or customer DB down |
| `DEADLINE_EXCEEDED` | 504 | Yes | Overall request deadline passed |

**Common types.**

| Type | Definition |
|---|---|
| `Uuid` | UUID v4 string, 36 characters |
| `Timestamp` | ISO 8601 UTC, e.g. `2026-11-01T14:03:22Z` |
| `SourceId` | String matching `^DOC-[0-9]{3}#s[0-9]{1,2}$`, e.g. `DOC-003#s2` (document plus section) |
| `AnswerStatus` | Enum: `ANSWERED`, `UNSUPPORTED`, `ESCALATION_OFFERED`, `TEMPORARILY_UNAVAILABLE` |
| `Role` | Enum: `customer`, `agent` |

**Privacy defaults (all contracts).** Logs hold correlation ID, subject ID, endpoint, status, latency, and error code. Logs never hold question text, answer text, tokens, or provider keys. Only the question and retrieved passages are sent to the external AI provider; customer identity is never sent. Provider credentials stay server-side.

**Overload (10,000 concurrent customers).** API instances are stateless. The rate limit is applied per `subject_id` and globally. Every outbound call has a deadline. When the system is saturated it returns 429 with `Retry-After` rather than queuing without bound.

---

## 3. Proposed values and decisions

| # | Value | Proposed | Justification | Status |
|---|---|---|---|---|
| V1 | Question length | 1-1,000 characters | Fits a support question; bounds AI input cost | Proposed |
| V2 | `top_k` passages | Default 5, max 8 | Enough context while limiting tokens | Proposed |
| V3 | Passage length sent to AI | Max 1,500 characters each | Bounds prompt size | Proposed |
| V4 | Overall inquiry deadline | 20 s | Leaves room for retrieval plus one AI call; to be confirmed after provider latency measurement | Proposed |
| V5 | Retrieval timeout | 2 s | Local index lookup should be fast | Proposed |
| V6 | AI provider timeout | 15 s | Must be less than V4 | Proposed |
| V7 | Customer DB timeout | 2 s | Lookup by key | Proposed |
| V8 | Rate limit, inquiries | 10 per minute per customer | Normal chat use; limits abuse | Proposed |
| V9 | Rate limit, escalations | 5 per hour per customer | Prevents queue flooding | Proposed |
| V10 | Escalation note length | 0-2,000 characters | Room for context | Proposed |
| V11 | Idempotency key retention | 24 hours | Covers client retries | Proposed |
| V12 | Feedback comment length | 0-500 characters | Short feedback | Proposed |
| V13 | Page size, agent queue | Default 25, max 100 | Keeps responses small | Proposed |
| V14 | Global capacity assumption | *Open, waiting on Vlad (requests/sec for 10,000 concurrent)* | Drives global rate limit | **Open** |

---

## 4. Contracts

### C1. Customer inquiry and answer

**Owner/caller:** `InquiryService`, called by the customer web UI. Version 1.0.
**Interface:** `POST /v1/inquiries`
**Authorization:** Role `customer` or `agent`. A customer may only access their own inquiries. Document scope is customer-visible sources only.

**Request body**

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `question` | string | Yes | No | 1-1,000 chars after trim; no control characters |
| `conversation_id` | Uuid | No | Yes | If present, must belong to caller |

**Response 200**

| Field | Type | Req. | Nullable | Notes |
|---|---|---|---|---|
| `inquiry_id` | Uuid | Yes | No | |
| `status` | AnswerStatus | Yes | No | |
| `answer` | string | Yes | Yes | Null unless `ANSWERED`; max 4,000 chars |
| `sources` | array of Source | Yes | No | Empty unless `ANSWERED`; max 8 |
| `escalation_offered` | boolean | Yes | No | True for `UNSUPPORTED` and `ESCALATION_OFFERED` |
| `answer_version` | string | Yes | No | Ties feedback (C6) to this answer |
| `correlation_id` | Uuid | Yes | No | |
| `contract_version` | string | Yes | No | `"1.0"` |

`Source`: `{ source_id: SourceId, title: string, section_title: string, url: string }`. The `url` must resolve through `GET /v1/sources/{source_id}`.

**Valid request**
```json
{ "question": "How do I set up the VPN on a new laptop?" }
```
**Success response**
```json
{
  "contract_version": "1.0",
  "inquiry_id": "b1d2c3e4-1111-4a22-8b33-9c44d55e6f77",
  "status": "ANSWERED",
  "answer": "Install the Acme VPN client, then sign in with your demo account and select the 'Campus' profile.",
  "sources": [{
    "source_id": "DOC-003#s2",
    "title": "VPN Setup Guide",
    "section_title": "Installing the client",
    "url": "/v1/sources/DOC-003%23s2"
  }],
  "escalation_offered": false,
  "answer_version": "ans-2026-11-01-001",
  "correlation_id": "6f1c2a9e-3b7d-4d0a-9c11-2f5e8a7b1d42"
}
```

**Validation and errors**

| Condition | Status / code | Safe message | Retry |
|---|---|---|---|
| Empty, over 1,000 chars, wrong type | 400 `VALIDATION_FAILED` | "Your question must be between 1 and 1000 characters." | No |
| No/invalid token | 401 `UNAUTHENTICATED` | "Please sign in again." | No |
| `conversation_id` not caller's | 403 `FORBIDDEN` | "You do not have access to this conversation." | No |
| Rate limit | 429 `RATE_LIMITED` + `Retry-After` | "Too many requests. Please wait and try again." | Yes |
| Retriever/AI/customer DB down | **200** with `status: TEMPORARILY_UNAVAILABLE`, `escalation_offered: true` | "We can't answer right now. You can send this to a support agent." | Yes |
| Deadline exceeded (20 s) | 504 `DEADLINE_EXCEEDED` | "This took too long. Please try again." | Yes |

*Design note:* a dependency failure on an inquiry returns 200 with a status so the UI can offer escalation and keep the question. Non-recoverable errors use the envelope. *(Confirm with Collins whether he prefers 503 here.)*

**Deadline/overload.** Overall deadline is 20 s (V4). The service passes the remaining time to C2 and C3.
**Persistence/idempotency.** The inquiry is stored (question, status, source IDs, answer version) before returning, so the question survives failures. No idempotency key is needed; repeated posts create separate inquiries.
**Privacy.** The question is stored in the inquiry record only. It is sent to the AI provider through C3 and never logged.

**Tests**

| Case | Expected |
|---|---|
| Valid supported question | 200, `ANSWERED`, at least 1 source that resolves |
| Unsupported question | 200, `UNSUPPORTED`, `escalation_offered: true`, no answer |
| Empty question; 1,001-char question | 400 `VALIDATION_FAILED` |
| No token | 401 |
| Another customer's `conversation_id` | 403 |
| AI provider timeout (mock) | 200 `TEMPORARILY_UNAVAILABLE`, question preserved |
| 11th request in a minute | 429 with `Retry-After` |

---

### C2. Retrieval and source access

**Owner:** `Retriever`.

**C2a. Method:** `retrieve(query: str, scope: RetrievalScope, top_k: int = 5, deadline_ms: int) -> RetrievalResult`
**Caller:** `InquiryService` (internal only).

| Input | Type | Req. | Constraints |
|---|---|---|---|
| `query` | string | Yes | 1-1,000 chars |
| `scope.visibility` | enum `customer`, `agent` | Yes | Limits to documents the caller may see |
| `top_k` | int | No | 1-8, default 5 |
| `deadline_ms` | int | Yes | 1-2000 |

**Output `RetrievalResult`:** `{ passages: [Passage], index_version: string }`, where `Passage = { source_id: SourceId, text: string (max 1,500 chars), score: float 0-1, rank: int }`. Passages are sorted by rank ascending. An empty `passages` list is a valid result (no support).
**Failures:** raises `RetrieverUnavailable` or `RetrieverTimeout`. `InquiryService` maps them to `TEMPORARILY_UNAVAILABLE`.

**C2b. Endpoint:** `GET /v1/sources/{source_id}`
**Authorization:** Any authenticated role, within scope. Customers cannot read agent-only documents.

**Success 200**
```json
{
  "contract_version": "1.0",
  "source_id": "DOC-003#s2",
  "document_title": "VPN Setup Guide",
  "section_title": "Installing the client",
  "text": "Download the Acme VPN client from the internal portal...",
  "document_version": "3",
  "correlation_id": "..."
}
```

| Condition | Status / code | Note |
|---|---|---|
| `source_id` fails the pattern | 400 `VALIDATION_FAILED` | |
| Source missing **or** out of scope | 404 `NOT_FOUND` | Same response for both, so existence of restricted documents isn't leaked |
| Retriever store down | 503 `DEPENDENCY_UNAVAILABLE` | Retryable |

**Missing-source behavior.** If the AI returns a source ID that is not in the retrieved set or does not resolve, the answer is rejected (C3 validation) and the inquiry becomes `UNSUPPORTED`.
**Privacy.** Queries are not logged. Passage text is sent only to C3.

**Tests:** known ID returns 200; unknown ID returns 404; agent-only ID requested by a customer returns 404; malformed ID returns 400; empty retrieval returns an empty list (not an error); retriever timeout (mock) raises `RetrieverTimeout`.

---

### C3. AI generation adapter

**Owner:** `GenerationAdapter`. It hides the provider so nothing else in the system knows which one is used (supports the coupling argument).
**Method:** `generate(request: GenerationRequest) -> GenerationResult`
**Caller:** `InquiryService` (internal only).

**`GenerationRequest`**

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `question` | string | Yes | 1-1,000 chars |
| `passages` | array of Passage | Yes | 1-8 items; only retrieved passages |
| `deadline_ms` | int | Yes | 1-15000 |
| `correlation_id` | Uuid | Yes | |

**`GenerationResult`**

| Field | Type | Req. | Nullable | Notes |
|---|---|---|---|---|
| `outcome` | enum `ANSWERED`, `INSUFFICIENT_EVIDENCE` | Yes | No | |
| `answer` | string | Yes | Yes | Null when `INSUFFICIENT_EVIDENCE`; max 4,000 chars |
| `cited_source_ids` | array of SourceId | Yes | No | Each must be in the request's passages |
| `adapter_version` | string | Yes | No | |

**Output contract checks (enforced by adapter):** at least one cited source for `ANSWERED`; every cited ID is in the supplied passages; otherwise the result is converted to `INSUFFICIENT_EVIDENCE`. Instructions found inside passage text are treated as data, not commands.

**Provider failure mapping**

| Provider event | Adapter exception | Resulting inquiry status |
|---|---|---|
| Timeout | `GenerationTimeout` | `TEMPORARILY_UNAVAILABLE` |
| Quota / 429 | `GenerationQuotaExceeded` | `TEMPORARILY_UNAVAILABLE` |
| 5xx / network | `GenerationUnavailable` | `TEMPORARILY_UNAVAILABLE` |
| Malformed output | `GenerationInvalidOutput` | `UNSUPPORTED` |

**Retry.** At most one retry, and only if time remains in the deadline. Automatic failover to a second provider is out of scope here (deferred).
**Privacy.** Sends only question and passage text. No customer ID, name, or email. API keys come from server-side configuration. Prompt/response bodies are not logged.

**Example request**
```json
{
  "question": "How do I set up the VPN on a new laptop?",
  "passages": [{"source_id": "DOC-003#s2", "text": "Download the Acme VPN client...", "score": 0.91, "rank": 1}],
  "deadline_ms": 15000,
  "correlation_id": "6f1c2a9e-3b7d-4d0a-9c11-2f5e8a7b1d42"
}
```

**Tests:** valid passages return `ANSWERED` with valid citations; model cites an ID not supplied becomes `INSUFFICIENT_EVIDENCE`; passage containing "ignore your rules" does not change behavior; each mocked provider failure maps as in the table; deadline of 1 ms raises `GenerationTimeout`.

---

### C4. Human escalation

**Owner:** `EscalationService`.
**Interface:** `POST /v1/escalations`
**Authorization:** Role `customer`. Creates an escalation owned by the caller.

**Request headers:** `Idempotency-Key: <Uuid>` (required).
**Request body**

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `inquiry_id` | Uuid | Yes | No | Must belong to caller |
| `question` | string | Yes | No | 1-1,000 chars; the customer may edit the prefilled text |
| `note` | string | No | Yes | 0-2,000 chars |
| `consent_to_share` | boolean | Yes | No | Must be `true` (user-reviewed content) |

**Response 201 (first) / 200 (duplicate with same key and body)**

| Field | Type | Notes |
|---|---|---|
| `escalation_id` | Uuid | |
| `status` | enum `NEW` | |
| `created_at` | Timestamp | |
| `acknowledgement` | string | "Your request was saved. Reference: ..." Returned only after the durable write |
| `correlation_id` | Uuid | |

**Valid request**
```json
{
  "inquiry_id": "b1d2c3e4-1111-4a22-8b33-9c44d55e6f77",
  "question": "VPN profile 'Campus' is missing after install.",
  "note": "Tried reinstalling twice.",
  "consent_to_share": true
}
```
**Success**
```json
{
  "contract_version": "1.0",
  "escalation_id": "e7a8b9c0-2222-4b33-8c44-0d55e66f7788",
  "status": "NEW",
  "created_at": "2026-11-01T14:05:10Z",
  "acknowledgement": "Your request was saved. Reference: e7a8b9c0.",
  "correlation_id": "..."
}
```

| Condition | Status / code | Retry |
|---|---|---|
| Missing/invalid field; `consent_to_share` false; missing `Idempotency-Key` | 400 `VALIDATION_FAILED` | No |
| 401 / 403 (wrong role or other customer's inquiry) | `UNAUTHENTICATED` / `FORBIDDEN` | No |
| Same key, different body | 422 `IDEMPOTENCY_MISMATCH` | No |
| Rate limit (5/hour) | 429 `RATE_LIMITED` | Yes |
| Database write failed | 503 `DEPENDENCY_UNAVAILABLE` (nothing saved, no acknowledgement) | Yes, same key |

**Idempotency/persistence.** The key and a hash of the body are stored for 24 h (V11). A repeat with the same key and body returns the original result with 200 and creates no new record. The acknowledgement is returned only after commit. The UI keeps the entered text if the call fails so the customer can retry.
**Privacy.** Stored: question, note, inquiry reference, customer ID. Not logged: question or note text. Not sent to the AI provider.

**Tests:** first submission returns 201; duplicate key and body returns 200 with the same ID and one DB row; same key with a different body returns 422; consent false returns 400; other customer's inquiry returns 403; DB failure (mock) returns 503 and zero rows; 6th escalation in an hour returns 429.

---

### C5. Agent review and update

**Owner:** `AgentQueueService`. **Authorization:** Role `agent` only. Customers get 403 on every endpoint.

**C5a. `GET /v1/agent/escalations?status=NEW&limit=25&cursor=...`**

| Param | Type | Constraints |
|---|---|---|
| `status` | enum `NEW`, `CLAIMED`, `RESOLVED` | Optional |
| `limit` | int | 1-100, default 25 |
| `cursor` | string | Optional, opaque |

Response: `{ items: [EscalationSummary], next_cursor: string|null }`, where `EscalationSummary = { escalation_id, status, question, created_at, owner_agent_id: string|null }`. Customer data is limited to the fields in C7's minimal profile.

**C5b. `POST /v1/agent/escalations/{id}/claim`**: no body. Succeeds only when `status = NEW`. Sets `owner_agent_id` to the caller and status to `CLAIMED`. Returns 200 with the updated escalation. If already claimed by someone else, returns 409 `CONFLICT`.

**C5c. `POST /v1/agent/escalations/{id}/transition`**

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `to_status` | enum `NEW`, `RESOLVED` | Yes | Must be allowed by table below |
| `resolution_note` | string | Cond. | Required for `RESOLVED`; 1-2,000 chars |
| `expected_version` | int | Yes | Optimistic locking |

**Permitted transitions**

| From | To | Who |
|---|---|---|
| `NEW` | `CLAIMED` | Any agent (via claim) |
| `CLAIMED` | `RESOLVED` | Owner agent only |
| `CLAIMED` | `NEW` (release) | Owner agent only |
| `RESOLVED` | (none) | Terminal |

| Condition | Status / code |
|---|---|
| Not an agent | 403 `FORBIDDEN` |
| Unknown `id` | 404 `NOT_FOUND` |
| Illegal transition, not the owner, or stale `expected_version` | 409 `CONFLICT` |
| Missing `resolution_note` for RESOLVED | 400 `VALIDATION_FAILED` |
| DB down | 503 `DEPENDENCY_UNAVAILABLE` |

**Overload.** Queue reads are paginated. Claim uses a conditional update so two agents can't both claim.
**Privacy.** Agents see only what is needed to resolve the request. Every transition is audit-logged with agent ID, old and new status, and correlation ID (not question text).

**Tests:** customer calling any C5 endpoint gets 403; two agents claim concurrently and exactly one gets 200 while the other gets 409; non-owner resolve returns 409; resolved to claimed returns 409; stale version returns 409; list pagination returns a stable `next_cursor`.

---

### C6. Feedback and improvement

**Owner:** `FeedbackService`. Learning is a *reviewed* loop with no automatic retraining.

**C6a. `POST /v1/feedback`** (role `customer`)

| Field | Type | Req. | Nullable | Constraints |
|---|---|---|---|---|
| `inquiry_id` | Uuid | Yes | No | Must belong to caller |
| `answer_version` | string | Yes | No | Must match the stored answer |
| `rating` | enum `HELPFUL`, `NOT_HELPFUL` | Yes | No | |
| `reason` | enum `INCORRECT`, `INCOMPLETE`, `WRONG_SOURCE`, `OTHER` | No | Yes | Only when `NOT_HELPFUL` |
| `comment` | string | No | Yes | 0-500 chars |

Response 201: `{ feedback_id, status: "PENDING_REVIEW", correlation_id }`. The record also stores `source_ids` and `index_version` from the answer.

**C6b. `GET /v1/agent/feedback?status=PENDING_REVIEW&limit=25`** (role `agent`): lists feedback with the linked question, answer version, and source IDs.

**C6c. `POST /v1/agent/feedback/{id}/review`** (role `agent`)

| Field | Type | Req. | Constraints |
|---|---|---|---|
| `decision` | enum `NO_ACTION`, `FIX_DOCUMENT`, `ADD_TEST_CASE` | Yes | |
| `reviewer_note` | string | Yes | 1-1,000 chars |

Status becomes `REVIEWED`. `ADD_TEST_CASE` adds the question to the evaluation set; `FIX_DOCUMENT` creates a document-update task for the content owner. Both are human-approved actions.

| Condition | Status / code |
|---|---|
| Invalid enum, `reason` with `HELPFUL`, comment too long | 400 `VALIDATION_FAILED` |
| Inquiry not the caller's | 403 `FORBIDDEN` |
| `answer_version` does not match | 409 `CONFLICT` |
| Duplicate feedback for same inquiry by same customer | 409 `CONFLICT` |
| Customer calls C6b/C6c | 403 `FORBIDDEN` |
| Already reviewed | 409 `CONFLICT` |

**Privacy.** Comments are visible only to agents. Comments are not logged and are not sent to the AI provider. **Retention (proposed):** 12 months.
**Tests:** valid feedback returns 201 and links to answer version; stale version returns 409; second feedback returns 409; customer reading the agent list returns 403; review sets `REVIEWED` and records the reviewer; `reason` with `HELPFUL` returns 400.

---

### C7. Existing customer database

**Owner:** `CustomerDirectoryAdapter`. It is the only module that knows the customer database schema. No real system is connected in this assignment; the adapter is specified against a fictional "CustomerDB".
**Method:** `get_customer_profile(customer_id: str, deadline_ms: int) -> CustomerProfile`
**Callers:** `InquiryService`, `EscalationService`. Read-only access.

| Input | Type | Constraints |
|---|---|---|
| `customer_id` | string | `^CUST-[0-9]{6}$`, e.g. `CUST-004821` |
| `deadline_ms` | int | 1-2000 (V7) |

**`CustomerProfile` (minimum fields only)**

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `customer_id` | string | No | |
| `display_name` | string | No | Max 80 chars |
| `tier` | enum `STANDARD`, `PRIORITY` | No | Used for queue priority |
| `account_status` | enum `ACTIVE`, `SUSPENDED` | No | |

Excluded: email, phone, address, payment data, password data. Anything beyond these fields requires a team decision.

**Example output**
```json
{ "customer_id": "CUST-004821", "display_name": "Jordan Example", "tier": "PRIORITY", "account_status": "ACTIVE" }
```

| Condition | Behavior |
|---|---|
| Bad ID format | Raises `InvalidCustomerId` (maps to 400) |
| Not found | Raises `CustomerNotFound` (maps to 404) |
| Timeout / DB down | Raises `CustomerDirectoryUnavailable` (maps to 503 where the profile is required) |

**Degradation.** Answering questions does not require the profile. If C7 is down, `InquiryService` continues without it. `EscalationService` saves the escalation with `customer_id` only and enriches it later. A dependency failure never blocks escalation.
**Caching (proposed, open).** Short-lived cache (60 s) of the profile, to be confirmed by Vlad against capacity.
**Privacy.** The profile is not sent to the AI provider. Only minimal fields are stored. Names are not logged.

**Tests:** valid ID returns profile with only listed fields; unknown ID raises `CustomerNotFound`; timeout (mock) raises `CustomerDirectoryUnavailable` and escalation still succeeds; malformed ID raises `InvalidCustomerId`; agent queue shows no fields beyond the profile.

---

## 5. Open items for the team

1. Confirm role names (`customer`/`agent`) and component names with Vlad's diagram.
2. Confirm `AnswerStatus` values and failure names with Collins's AI flows (C1 and C3).
3. Vlad to supply the capacity assumption (V14) so rate limits and the cache can be finalized.
4. Decide whether a dependency failure on C1 returns 200 with a status (current draft) or 503.
5. Confirm V4 and V6 timeouts after the B05 provider latency measurements.
6. Record team decisions in the table in Section 3 (change *Proposed* to *Team-approved*).

## 6. Contribution note

*(Hanlin: add your own record of what you drafted, who reviewed it, and which comments you resolved.)*
