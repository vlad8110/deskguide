# Unit 3 — Quality, Security, Reliability, and Design Verification Plan

**Project:** DeskGuide · CMSC 495, Team 4
**Section lead:** David Warren (@dwarren10), Solutions Engineer
**Team review:** Vlad (@vlad8110) for architecture/capacity; Hanlin (@Henry-Wong001) for contracts; Collins (@MrAmpossible) for AI, escalation and feedback
**Work item:** [#14](https://github.com/vlad8110/deskguide/issues/14)
**Draft:** October 31, 2026; **updated:** November 2, 2026. **Design proposals only: no software tests, 10,000-user capacity results, external-provider tests, real customer database connections or reviewer approvals are claimed.**

**November 2 alignment:** The [Nov 2 verification addendum](david-verification-alignment-nov2.md) supersedes earlier *proposed* timeout, contract, registered-ID, session, capacity, retention, release and measurement details where they differ. It includes N01–N15 planned regression tests, a pre-labeled 20-question B12 candidate manifest and denominator/accounting rules. Vlad's latest working decisions and the actual PR review links are recorded there. No test execution or final approval is inferred.

This document supplies verification evidence to the three graded Unit 3 deliverables (component architecture diagram, typed interface contracts, and 500-word rationale); it is **not** a fourth graded deliverable. Apply [assignment requirements](assignment-requirements.md), [work plan](work-plan.md), [architecture](architecture.md), [interface contracts](interface-contracts.md), [AI integration](ai-integration.md) and the [backlog implementation map](../backlog/implementation-map.md). Where architecture or interface decisions remain open, the expected result is explicitly **proposed**, not approved.

## 1. Verification method and evidence requirements

Methods: **I** = document/diagram inspection; **C** = API/schema review; **M** = deterministic mock/fixture test after implementation; **E** = synthetic end-to-end integration test after implementation; **L** = approved, staged load test, not authorized under this design issue. Use synthetic customers and documents only. Every eventual execution record must give check ID, test data/version, environment, date, outcome, evidence link, defect reference and reviewer. A checklist is not evidence of execution.

### 1.1 Requirements traceability matrix

| Requirement | Design acceptance question | Evidence and cases to inspect | Responsible owner; verification role | Current status |
| --- | --- | --- | --- | --- |
| **R1 — AI customer inquiries** | Can authorized customers obtain answers grounded in permitted, versioned passages, with unsupported outputs safely rejected? | Diagram and C1–C3/C10, normal/unsupported AI sequence, V01–V05, B07/B10/B12 | Collins/Hanlin; David validates source and error paths | Planned; diagram/contracts pending final review |
| **R2 — human escalation** | Is escalation confirmed by the customer, durably saved before acknowledgement, idempotent on retry, and accessible only to authorized agents? | C4a–C4e/C5/C9, agent state workflow, V06–V10, B11 | Collins/Hanlin; David tests reliability/permissions | Planned; exact contracts pending |
| **R3 — learn from patterns** | Do reviewed feedback, evaluation, versioning, release approval and rollback occur without automatic unsupervised retraining? | C6/C9, reviewed feedback flow, V11–V12, B13/P04 | Collins; David reviews governance/regression | Planned; retention and release ownership open |
| **R4 — 10,000 concurrent customers** | Are session semantics, peak rate, sizing constraints, overload and a future test plan explicit without claiming achieved capacity? | Workload and phased load model in §4, architecture decisions, V20–V25, P01 | Vlad + David; Collins checks AI quotas, Hanlin checks errors | Working assumptions; **not measured** |
| **R5 — existing customer database** | Is access constrained to authorized minimal fields through an adapter, with object-level isolation and safe unavailability handling? | C7, customer-data boundary, V13–V15, P02 | Vlad/Hanlin; David reviews privacy/isolation | Design-only; no real database connection |
| **R6 — junior-developer maintainability** | Are modules cohesive and independently testable with documented boundaries and repeatable synthetic fixtures? | Diagram, C1–C10, setup/ownership, V17–V19, B03/B04/B06 | Whole team; David checks testability | Review pending |

**Backlog continuity:** B04 API validation; B07 stable sources; B09 role authorization; B11 provider failure + single-save escalation; B12 fixed quality dataset and sequential latency; B16/B22 security/regression. B17 is consolidated into B11, not a second provider-failover feature. Production additions P01–P04 are **design scope**, not claims of implemented features. The local Flask/SQLite prototype and sequential demo measurements are not 10,000-customer capacity evidence.

## 2. Security, privacy and data-integrity design checks

1. **Customer browser/agent UI -> API boundary:** all browser input is untrusted. Define types, length/size limits and schema validation. Enforce authentication and customer/agent/administrator authorization on the server, never only in UI. Enforce CSRF protection for the proposed server-side cookie sessions, safe output encoding, and rate limiting. Explicitly reject forged role/customer claims.
2. **API -> customer-data adapter:** derive tenant and customer scope from a verified server-side identity; do not trust a client-provided customer ID alone. Authorize each record operation and returned field. Deny cross-tenant/cross-customer requests without leaking protected record existence. Define the minimal permitted fields and database ownership before implementing C7.
3. **Knowledge retrieval -> external AI:** retrieved documents are **data**, not instructions. Enforce document/tenant/source-version permissions before retrieval and after generated citations. Never permit retrieved text to override authentication, send secrets, change application rules or issue database commands. Minimize content sent to external providers; do not send credentials or full customer history. Verify provider retention/data-use policies later before service selection (see [privacy Issue #8](https://github.com/vlad8110/deskguide/issues/8)).
4. **Model output -> answer presentation:** require a structured response whose source IDs/versions are in the actual, authorized retrieved set. Reject missing, stale, invalid or cross-tenant citations. A resolvable citation is **not automatically** proof of factual support: C10 needs a separate runtime passage-support checker (Collins's executable thresholds remain pending). Keep the independently labeled 20-case B12 manual evaluation separate from runtime evidence gating. If evidence is inadequate or output malformed, give a clear limitation and offer human escalation; never fabricate a citation.
5. **Escalation -> persistence/agent queue:** obtain explicit user confirmation of the exact support-request content; allow edit/cancel. A successful acknowledgement follows a durable commit, not merely client send or queue admission. Require pre-registered, server-issued, customer-/operation-scoped IDs under C4a–C4e with an atomic receipt/content save and persistent uniqueness constraint; same key+payload returns same saved request, same key+different payload returns a safe conflict. When commit outcome is unknown, preserve the question and offer status lookup/retry using the same key; **do not claim saved**.
6. **Feedback -> change management:** associate feedback with trusted inquiry metadata and, when one exists, answer/source/prompt/model versions and access scope; only authorized humans can review/publish approved changes after regression evaluation. Maintain revision/rollback records. Do not promise automated model retraining.
7. **Operational hygiene:** no real credentials, customer records or sensitive document text in public GitHub, URLs, debug logs, analytics, response errors or test screenshots. Encrypt transport in production design; constrain service credentials to least privilege; log opaque IDs, time, component and safe outcome codes. Define retention/deletion and backup behavior before real deployment; none is approved by Unit 3 documents.

### 2.1 Interface error vocabulary proposed for Hanlin

Use stable, typed error responses carrying a correlation ID but no internal stack or provider text. Hanlin must approve exact field names, HTTP mappings and retry semantics before final specification. Align to Draft 3.1 uppercase error codes: CSRF_FAILED (403), SUBMISSION_ID_EXPIRED (410), CONFLICT (409), RATE_LIMITED (429), SERVICE_BUSY (503), SAVE_OUTCOME_UNCERTAIN (503), DEPENDENCY_UNAVAILABLE (503), DEADLINE_EXCEEDED (504). A delivered controlled provider fallback is 200 temporarily_unavailable but is **not** a validated AI answer. Never expose unsanitized provider error details; do not retry non-idempotent operations without the same stable key.

## 3. Planned verification scenarios — **none executed**

| ID | Requirement | Scenario and expected result | Method / coordinating owner |
| --- | --- | --- | --- |
| V01 | R1 | Authorized supported inquiry first passes C10 `prepare_evidence` on permitted C2 retrieval **before** any C3 provider call, then passes C10 post-generation citation/source/version/answer support checks **before** display; failed gates never publish a candidate | C/M/E; Collins + Hanlin; David checks sequence |
| V02 | R1/R2 | Unmatched/ambiguous/unsupported query or unavailable **pre-generation** evidence gate prevents C3 call, returns honest limitation/clarification or customer-initiated agent option, and creates no support request without confirmation | C/M/E; Collins + David |
| V03 | R1/R5 | Stale, missing, or other-tenant source ID is rejected before display | M/E; David + Collins |
| V04 | R1/R6 | Hostile source text instructing model to ignore policies, change roles or exfiltrate data is handled as untrusted text | M/E; David + Collins |
| V05 | R1 | Empty, oversized, malformed, HTML/script or SQL-bearing input is validated and safely rendered; no injection or unauthorized provider call | C/M; Hanlin + David |
| V06 | R2 | User reviews and explicitly confirms escalation; only durably saved record produces acknowledgement and stable request ID | C/M/E; Collins + Hanlin |
| V07 | R2 | Repeated identical customer/operation/server-registered ID and payload creates one persistent escalation or reply and returns original receipt | M/E; David + Hanlin |
| V08 | R2 | Same registered ID with changed payload yields 409 CONFLICT, no second record or data leak | C/M; David + Hanlin |
| V09 | R2 | DB save fails or commit status unknown: no false acknowledgement; question preserved; C4c lookup or retry with same ID and payload, never auto-register replacement | M/E; Collins + David |
| V10 | R2/R5 | Customer calls agent-only API, administrator attempts support-content read, or caller changes target customer/request ID: denied with no record disclosure | C/M/E; Hanlin + David |
| V11 | R3 | Feedback tied to trusted inquiry even without answer ID; only evaluated version with independent non-author approval can be released | C/M; Collins + David |
| V12 | R3 | Evaluated update regresses fixed quality dataset: change rejected; exact evaluated version required, rollback restores previously approved version | M/E; Collins + David |
| V13 | R5 | Explicit account-status operation reads only customer_id/account_status from server-scoped customer record and makes zero AI calls | C/M; Hanlin + David |
| V14 | R5 | Cross-customer or cross-tenant lookup denied despite valid login and modified IDs | M/E; Hanlin + David |
| V15 | R5 | Customer database timeout, malformed response or unavailable dependency produces bounded safe degradation, no fabricated data | M/E; Hanlin + Vlad |
| V16 | R1/R2/R4 | AI timeout, provider quota/429, malformed provider response: controlled fallback, original question retained, no raw errors/secrets | M/E; Collins + David |
| V17 | R6 | Every diagram arrow has named C1–C10 contract, source, destination, authorization context and failure path | I/C; David + team |
| V18 | R6 | Junior developer can use synthetic fixtures/mock provider and documented setup to reproduce focused component tests | I/M; Vlad + David |
| V19 | R5/R6 | Git diff and final export contain no tokens, passwords, private customer data or test secrets | I/secret-scan when available; David + team |
| V20 | R4 | Proposed 10,000 active sessions with selected request mix have documented quotas, resources, deployment and result metrics | I/L later; Vlad + David |
| V21 | R4 | Bounded 2x burst causes safe 429/503/admission rejection, **no AI waiting queue** and no unbounded growth | M/L later; Vlad + Hanlin |
| V22 | R4 | Provider capacity well below inbound demand triggers bounded admission, honest customer fallback, no quota overrun | M/L later; Collins + David |
| V23 | R2/R4 | Node/session restart does not lose committed requests, leak customer context or create duplicate tickets | M/L later; Vlad + David |
| V24 | R4 | Provider/DB service recovery avoids retry storms and returns to normal without false acknowledgements | M/L later; Vlad + Collins |
| V25 | R4 | Mocked-provider load and limited real-provider smoke reported as separate evidence, neither falsely implying full-scale capacity | I/L later; David + team |

**Early B12 answer-quality gate (not a production SLA):** fixed 20 questions = 12 supported, 4 unsupported and 4 ambiguous/misleading. At least 10/12 supported answers must match the actual source passages and all 4 unsupported must trigger fallback; inspect ambiguous cases individually. Record question set/version, prompt/model/retrieval configuration, reviewer judgments, and ten sequential response measurements including each latency, median, maximum, model, hardware/network environment and error/timeouts. No B12 demo score demonstrates R4 scalability.

## 4. 10,000-customer capacity **design and future validation**

### 4.1 Workload definition and illustrative sizing

**Vlad's selected design workload (still untested): 10,000 concurrent active customer sessions averaging one inquiry per minute, or about 166.67 new inquiries/second.** This is not 10,000 simultaneous model calls, nor measured capacity. Retrieval volume, per-session request timing, customer-data lookups, feedback, escalation and model-call fraction remain to be specified. Vlad's first-session scenarios use five seconds solely as an **illustrative mean response-time assumption**, not a tested result or acceptance threshold.

| Scenario | Inquiry per customer | Inquiry rate at 10,000 customers | In-flight work at illustrative 5-second mean |
| --- | --- | --- | --- |
| Light | 1 / 600 seconds | 16.7 inquiries/s | about 84 |
| Lighter sensitivity | 1 / 300 seconds | 33.3 inquiries/s | about 167 |
| **Selected design workload** | **1 / 60 seconds** | **166.67 inquiries/s** | **about 834** |

Illustrative in-flight estimate = arrival rate × mean service/response time (Little's Law; valid for stable steady-state conditions). **166.67 inquiries/s is about 10,000 incoming inquiries/minute (600,000/hour)**. If every inquiry invokes an external model, the provider must accommodate that order of demand, or the architecture must explicitly limit/reject/route overload. Do **not** assume third-party quotas, caching, agent capacity or response time suffice. A separate 10,000-**simultaneous-requests** scenario remains open for clarification.

**Remaining design decisions from Vlad/team:** specify the selected-session workload's arrival distribution, payload/document sizes, model-call fraction, customer-data lookup frequency, escalation/feedback rates, provider quota and budget, login/session design, deployment and resource bounds. Vlad proposes 333.33/s for two minutes and a separate 10,000-arrivals-in-one-second **synthetic overload** scenario; these require test-environment and stop-condition approval. Establish measurable p95/p99, throughput, error, queue-wait, availability and recovery gates **before** executing a test; no invented passing thresholds here.

### 4.2 Architecture constraints to review

The local Flask+SQLite prototype remains a valid educational demo but is not proof of production throughput or safe high-write concurrency. For the new production **design**, Vlad must identify: frontend ingress/admission control, replication or deployment shape, stateless/shared customer sessions, suitably durable shared escalation storage, customer-data isolation, model gateway with bounded concurrency/deadlines, human-agent workflow capacity, metrics/logging and outage handling. A modular application and deployed services are competing options; no production database/provider is approved by this verification plan. Keep AI logic separate from deterministic auth, database access and escalation. Explicitly show which resources scale independently and which are constrained by quotas.

### 4.3 Staged validation — **proposal only, no large load authorized**

| Phase | Synthetic traffic proposal | Dependencies | Gate / evidence |
| --- | --- | --- | --- |
| A: smoke | 1–10 clients; answer, unsupported, retries, roles | Mock provider + synthetic DB | Validate C1–C7, source IDs, denial and single-save |
| B: baseline | 100 then 1,000 sessions; ~5 minutes each | Mock provider + synthetic DB | p50/p95/p99, throughput, CPU/RAM, rate and errors |
| C: capacity | Ramp to 5,000 then 10,000 sessions; proposed 10-minute hold near 166.67 inquiries/s after ramp | Mock provider + synthetic DB | Offered vs admitted/answered/fallback rates, session count, queues and correctness |
| D: burst | Proposed 333.33 inquiries/s for two minutes; bounded, preapproved test | Mock provider + synthetic DB | 429/503/backpressure, no resource runaway or duplicate saves |
| D2: synchronous overload | Separate synthetic **10,000 arrivals in one second** only if environment/stop conditions approved | Mock provider + synthetic DB | Safe admission and recovery; never route this volume to a live AI service |
| E: recovery | Simulate provider 429/timeout, customer DB delay and node restart | Mock failures | Recover safely; never acknowledge unsaved escalation |
| F: external API smoke | Small sample only **after** team/provider approval and quota/cost check | Selected live provider, fictional data only | Compatibility, citation checks, observed timeouts; **not full 10k capacity evidence** |

Suggested tooling, subject to team approval: reproducible Locust or k6 script and versioned synthetic fixtures. Record deployment shape, available CPU/RAM, connection pools, DB/index size, per-customer think time, traffic mix and durations. Measure offered vs accepted throughput, active sessions, p50/p95/p99 latency per endpoint, completion/error/timeout counts, 429/503, request in-flight count, queue depth, provider concurrency, persistence success/latency, resource use and time to recovery. **Never** execute substantial third-party traffic, deploy paid services or connect actual customer data without explicit approval.

Non-negotiable correctness criteria for eventual tests: zero cross-customer disclosures in the sampled scenarios; no false success acknowledgement for a failed/unconfirmed save; no duplicate escalation for a repeated scoped idempotency key; no fabricated source citations. Quantitative latency/throughput/availability targets remain open team decisions. Mocked-provider throughput validates **only the modeled application boundary**, not real provider quota, cost, production storage or full system capability.

**Overload behavior:** apply per-customer rate limits and global admission control, independently cap AI concurrency and queue length, return typed safe 429/503 with bounded retry guidance, and prioritize correct escalation state. Avoid retry storms and never treat an unlimited support queue as the fallback for unlimited model demand. If the database is unavailable, display unsaved/unknown state honestly and preserve the user's question for later retry.

## 5. Cross-section design review and gap register

The current published architecture, interface and AI files are **working frameworks**, not finalized detailed design. These are **risks/questions to resolve**, not asserted implementation defects. Confirm each against the reviewed pull request and exact commit.

| Finding | Severity | Scope / risk if absent | Responsible owner | Proposed verification / resolution | Status |
| --- | --- | --- | --- | --- | --- |
| F01 | High | **Vlad selected 10,000 sessions at 166.67 inquiries/s**; provider feasibility, mix, deployment/storage model and capacity targets remain unproven | Vlad + David + Collins | Approve model-call fraction, provider quotas, production resource/DB sizing and test gates in decisions.md | **Open — feasibility and targets; workload selected** |
| F02 | High | Cross-customer leakage through C1/C2/C5/C7 or direct object references | Vlad + Hanlin; David verifies | Server-side tenant scope and per-record access at every boundary; V10/V14 | Open — design review |
| F03 | High | Double escalation or false acknowledgement after network retry | Hanlin + Collins; David verifies | Stable submission ID, durable unique scoped key, conflict and outcome-unknown handling; V06–V09 | Open — design review |
| F04 | High | AI quota/price cannot sustain chosen workload | Collins + Vlad | Document actual selected provider quotas and safe degradation; V16/V22 | Open — provider choice |
| F05 | High | Incorrect or malicious retrieval can yield plausible unsupported guidance | Collins + David | Source/version/permission checks, 20-case evaluation, adversarial V03/V04 | Open — design review |
| F06 | Medium | Diagram interactions and C1–C7 contracts may diverge | All; David coordinates check | Cross-reference arrows, paths, roles, schemas and error states | Open — Sunday review |
| F07 | Medium | “Learning” may imply unsupervised model retraining | Collins | Document human gate, evaluation, version/rollback semantics; V11/V12 | Open — design review |
| F08 | Medium | Junior maintainer cannot reproduce behavior or review config securely | Vlad + team | Provide mock fixtures, component boundaries, non-secret setup and test entry points; V17–V19 | Open — maintainability review |

### 5.1 Cross-document consistency checklist

| Ref | Required match | Status |
| --- | --- | --- |
| X01 | C1 → C2 retrieval → **C10 `prepare_evidence` (M5, before C3)** → C3 generation → **C10 `validate` (M5, after C3)** → C1 display must be explicit in both written walkthrough and component diagram; each failed gate produces controlled fallback without unapproved C3 calls or unsupported display | Sequence corrected in A3b and the component diagram; [David confirmed his specific finding resolved](https://github.com/vlad8110/deskguide/pull/15#issuecomment-6618357810). Combined-version approval and execution remain pending. |
| X02 | C4 confirmed escalation -> durable save -> ack -> C5 agent view, including duplicate/unknown commit | Pending |
| X03 | C7 customer adapter shows trusted customer identity, minimal fields, denied access and outage path | Pending |
| X04 | C6 feedback identifies answer/version, reviewer gate, regression and rollback | Pending |
| X05 | 400/401/403/404/409/429/503/timeout labels and response structures agree across diagram/flows/contracts | Pending |
| X06 | R4 rate is now selected (166.67/s); production deploy/storage design, provider feasibility and numeric acceptance targets still require agreement | **Partially clarified; not verified** |
| X07 | Rationale defends actual module boundaries, coupling/cohesion and major tradeoff with authoritative citation | Pending Vlad's final 500 words |
| X08 | Correlation ID, source ID/version, escalation ID and idempotency key are distinct and scoped | Pending |

**Reviewer rule:** mark an item “verified” only after reviewing the exact PR/commit and linking the evidence. If a finding remains open, record an owner, impact, mitigation and team acceptance rather than pretending it disappeared.


### 5.2 October 31 response to Vlad's D01–D21 working proposals (not final sign-off)

Reviewed [Vlad's proposed decision log](https://github.com/vlad8110/deskguide/blob/docs/unit-3-architecture-review/docs/unit-3/design-decisions-and-review-log.md), [500-word rationale draft](https://github.com/vlad8110/deskguide/blob/docs/unit-3-architecture-review/docs/unit-3/design-rationale.md), and the in-review contract/AI drafts. This is a **design review of proposals**, not a full implementation test or team approval. Detailed feedback is posted to architecture PR #15 and linked from Issue #14.

- **D01/D11/D13/D20 — acceptance denominators:** Select 166.67/s as offered traffic, while reporting distinct admitted, answered-with-evidence, supported fallback, throttled, failed and timed-out rates. The suggested 95% of *successful AI answers* within 15s may appear passing even if most customers receive no AI answer; define a separate answer-availability/admission gate at the offered workload. Using Vlad's cited 500 calls/min provider example and one call/inquiry, only 5% of 10,000 incoming inquiries/min can make the call, independent of application replication. Provider/model/account quotas and realistic model-call fraction remain blocking evidence.
- **D09/D17 — retry lifetime:** A raw, client-generated UUID that has disappeared after retention cannot be distinguished from a valid first-time UUID. Propose durable scoped idempotency receipt/tombstone with minimal data and explicit finite recognition period, or server-issued/verifiable expiry tokens. Reused key+same payload returns prior request; reused key+different payload conflicts; old/unknown key never silently creates a second ticket. Specify the privacy/backup deletion tradeoff. Apply equivalent semantics to customer replies.
- **D07/D16/D18 — access and sessions:** Scope each object by verified server identity. Distinguish customer record ownership from agent assignment, and document admin-only rights. For proposed server-side sessions, set and test *idle* and *absolute* expiry separately, session rotation, logout invalidation, CSRF enforcement and cookie flags. Define whether logout cancels other active sessions and how session cleanup propagates across replicas.
- **D12 — agent race checks:** Atomically claim queued work once; reject stale version/non-owner transitions; a customer reply racing with resolution must not reopen a resolved ticket; duplicate customer reply with same ID must not create two messages. Confirm release-to-queue from waiting/in-review and preserve an auditable reason.
- **D14 — circuit breaker:** Verify one global half-open trial with a leased/versioned state, recover expiry after worker crash, and ignore late trials. Reevaluate three consecutive failures in a high-volume system and measure how often shared PostgreSQL breaker-state writes contend; do not hold a DB lock across provider calls. Quota exhaustion should respect quota reset instead of reopening every 30 seconds.
- **D03/D04/D05 — evidence, outage and feedback:** Test structural citation checks separately from semantic support. Check that 200/temporarily_unavailable is counted as fallback, **not** successful AI answer. Accept feedback tied to inquiry_id without answer_id for unsuccessful inquiries, but require ownership, valid outcome, and retention/expiry consistency.
- **D19/D21 — rationale/final review:** The rationale draft contains **500 whitespace-delimited words** excluding heading/references (local count); it remains a proposal tied to unapproved choices. Before approval, update the diagram and contracts to the same reviewed revision and record actual reviewer approval and final submission evidence.

## 6. Team milestones, contribution evidence and final-release gate

- **October 31 by 6 p.m. ET:** submit this drafted section from a focused branch and PR referencing Issue #14; ask Vlad for review. Report capacity and contract assumptions needing cross-team decisions.
- **November 1:** compare Vlad's diagram (M1–M9) and Hanlin's proposed C1–C10 with Collins's detailed flows; log X01–X08 outcomes and specific corrective PR comments. Avoid approval without completed review.
- **November 2:** resolve findings or document explicit acceptance; contribute concise reliability/coupling text to Vlad's ~500-word rationale; confirm exact reviewed commit and record actual contribution/reviewer evidence.
- **November 3 by 11:59 p.m. ET:** verify the integrated diagram, interface tables, 500-word rationale/reference and legible export; ensure LEO submission instructions and individual obligations are confirmed. Vlad coordinates final submission; no submission is claimed here.

**Design-review exit criteria:** all R1–R6 have traceable design evidence or an accepted gap; high-severity findings resolved/explicitly accepted; C1–C10 identifiers/flows/diagram consistent; privacy and durable escalation semantics documented; capacity remains labeled **design target**; one teammate reviewed the PR; team contributions and final approvals cite real evidence; the final specification contains the **three required** deliverables and a correctly counted 500-word rationale. Do not close #14 solely because the draft exists.

| Date | Check(s) | PR/commit reviewed | Evidence link | Observed result | Reviewer |
| --- | --- | --- | --- | --- | --- |
| Nov 1 | X01–X08 / architecture review | [PR #15](https://github.com/vlad8110/deskguide/pull/15) | [David's COMMENTED review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5730726420) | Initial/revised architecture reviewed; final integrated version not yet approved | David |
| Nov 2 | C1–C10 / contracts review | [PR #17 at 0e7f855](https://github.com/vlad8110/deskguide/pull/17) | [David's COMMENTED review](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5738959296) | Draft 3.1 reviewed; remaining decisions pending | David |
| Nov 2 | Verification package peer review | [PR #18 at a9912c9](https://github.com/vlad8110/deskguide/pull/18) | [Vlad's COMMENTED review](https://github.com/vlad8110/deskguide/pull/18#pullrequestreview-5744463050) | Alignment requested; November 2 supplement responds, no approval yet | Vlad |
| Pending | V01–V25 | Not yet implemented/executed | None | **No test results available** | Pending |

## 7. Sources and disclosure

- Team sources: [R1–R6 requirements](assignment-requirements.md), [Vlad's capacity options](architect-first-session.md), [C1–C7 framework](interface-contracts.md), [AI workflow framework](ai-integration.md), [backlog map](../backlog/implementation-map.md), [Issue #14](https://github.com/vlad8110/deskguide/issues/14), and [Issue #8 privacy](https://github.com/vlad8110/deskguide/issues/8).
- OWASP. (2023). *API Security Top 10: API1 Broken Object Level Authorization*. https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ — object-level authorization.
- NIST. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. https://doi.org/10.6028/NIST.AI.100-1 — AI risk evaluation, governance and oversight.
- Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. *Communications of the ACM, 15*(12), 1053–1058. https://doi.org/10.1145/361598.361623 — modular abstraction and change isolation.

**AI-assisted drafting disclosure:** this draft was produced with AI writing assistance for David's review. The named student should validate accuracy, revise as needed and follow the instructor's attribution rules before submitting. It does not establish personal approval, test execution or peer review.

## Combined design follow-up

Use [N16–N21](david-verification-alignment-nov2.md#g-combined-review-additions--november-3) for the inquiry-bound evidence expectation, exact-answer policy, provider-versus-answer metrics, stage-dependent responses, outbound eligibility and deterministic account answer identity. These extend the existing planned scenarios; no tests have been executed. Hanlin is the accepted backup release authorizer, subject to explicit permission and non-author enforcement.
