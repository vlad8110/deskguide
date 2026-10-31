# Unit 3 — Quality, Security, Reliability, and Design Verification Plan

**Project:** DeskGuide · CMSC 495, Team 4  
**Section lead:** David Warren (@dwarren10), Solutions Engineer  
**Team review:** Vlad (@vlad8110) for architecture/capacity; Hanlin (@Henry-Wong001) for contracts; Collins (@MrAmpossible) for AI, escalation and feedback  
**Work item:** [#14](https://github.com/vlad8110/deskguide/issues/14)  
**Draft:** October 31, 2026. **Design proposals only: no software tests, 10,000-user capacity results, external-provider tests, real customer database connections or reviewer approvals are claimed.**

This document supplies verification evidence to the three graded Unit 3 deliverables (component architecture diagram, typed interface contracts, and 500-word rationale); it is **not** a fourth graded deliverable. Apply [assignment requirements](assignment-requirements.md), [work plan](work-plan.md), [architecture](architecture.md), [interface contracts](interface-contracts.md), [AI integration](ai-integration.md) and the [backlog implementation map](../backlog/implementation-map.md). Where architecture or interface decisions remain open, the expected result is explicitly **proposed**, not approved.

## 1. Verification method and evidence requirements

Methods: **I** = document/diagram inspection; **C** = API/schema review; **M** = deterministic mock/fixture test after implementation; **E** = synthetic end-to-end integration test after implementation; **L** = approved, staged load test, not authorized under this design issue. Use synthetic customers and documents only. Every eventual execution record must give check ID, test data/version, environment, date, outcome, evidence link, defect reference and reviewer. A checklist is not evidence of execution.

### 1.1 Requirements traceability matrix

| Requirement | Design acceptance question | Evidence and cases to inspect | Responsible owner; verification role | Current status |
| --- | --- | --- | --- | --- |
| **R1 — AI customer inquiries** | Can authorized customers obtain answers grounded in permitted, versioned passages, with unsupported outputs safely rejected? | Diagram and C1–C3, normal/unsupported AI sequence, V01–V05, B07/B10/B12 | Collins/Hanlin; David validates source and error paths | Planned; diagram/contracts pending final review |
| **R2 — human escalation** | Is escalation confirmed by the customer, durably saved before acknowledgement, idempotent on retry, and accessible only to authorized agents? | C4/C5, agent state workflow, V06–V10, B11 | Collins/Hanlin; David tests reliability/permissions | Planned; exact contracts pending |
| **R3 — learn from patterns** | Do reviewed feedback, evaluation, versioning, release approval and rollback occur without automatic unsupervised retraining? | C6, reviewed feedback flow, V11–V12, B13/P04 | Collins; David reviews governance/regression | Planned; retention and release ownership open |
| **R4 — 10,000 concurrent customers** | Are session semantics, peak rate, sizing constraints, overload and a future test plan explicit without claiming achieved capacity? | Workload and phased load model in §4, architecture decisions, V20–V25, P01 | Vlad + David; Collins checks AI quotas, Hanlin checks errors | Working assumptions; **not measured** |
| **R5 — existing customer database** | Is access constrained to authorized minimal fields through an adapter, with object-level isolation and safe unavailability handling? | C7, customer-data boundary, V13–V15, P02 | Vlad/Hanlin; David reviews privacy/isolation | Design-only; no real database connection |
| **R6 — junior-developer maintainability** | Are modules cohesive and independently testable with documented boundaries and repeatable synthetic fixtures? | Diagram, C1–C7, setup/ownership, V17–V19, B03/B04/B06 | Whole team; David checks testability | Review pending |

**Backlog continuity:** B04 API validation; B07 stable sources; B09 role authorization; B11 provider failure + single-save escalation; B12 fixed quality dataset and sequential latency; B16/B22 security/regression. B17 is consolidated into B11, not a second provider-failover feature. Production additions P01–P04 are **design scope**, not claims of implemented features. The local Flask/SQLite prototype and sequential demo measurements are not 10,000-customer capacity evidence.

## 2. Security, privacy and data-integrity design checks

1. **Customer browser/agent UI -> API boundary:** all browser input is untrusted. Define types, length/size limits and schema validation. Enforce authentication and customer/agent/administrator authorization on the server, never only in UI. Define CSRF protection if cookie sessions are chosen, safe output encoding, and rate limiting. Explicitly reject forged role/customer claims.
2. **API -> customer-data adapter:** derive tenant and customer scope from a verified server-side identity; do not trust a client-provided customer ID alone. Authorize each record operation and returned field. Deny cross-tenant/cross-customer requests without leaking protected record existence. Define the minimal permitted fields and database ownership before implementing C7.
3. **Knowledge retrieval -> external AI:** retrieved documents are **data**, not instructions. Enforce document/tenant/source-version permissions before retrieval and after generated citations. Never permit retrieved text to override authentication, send secrets, change application rules or issue database commands. Minimize content sent to external providers; do not send credentials or full customer history. Verify provider retention/data-use policies later before service selection (see [privacy Issue #8](https://github.com/vlad8110/deskguide/issues/8)).
4. **Model output -> answer presentation:** require a structured response whose source IDs/versions are in the actual, authorized retrieved set. Reject missing, stale, invalid or cross-tenant citations. A resolvable citation is **not automatically** proof of factual support: use the fixed labeled evaluation set and manual passage-to-answer checking. If evidence is inadequate or output malformed, give a clear limitation and offer human escalation; never fabricate a citation.
5. **Escalation -> persistence/agent queue:** obtain explicit user confirmation of the exact support-request content; allow edit/cancel. A successful acknowledgement follows a durable commit, not merely client send or queue admission. Require stable scoped idempotency keys with a persistent uniqueness constraint; same key+payload returns same saved request, same key+different payload returns a safe conflict. When commit outcome is unknown, preserve the question and offer status lookup/retry using the same key; **do not claim saved**.
6. **Feedback -> change management:** associate feedback with answer/source/prompt/model versions and access scope; only authorized humans can review/publish approved changes after regression evaluation. Maintain revision/rollback records. Do not promise automated model retraining.
7. **Operational hygiene:** no real credentials, customer records or sensitive document text in public GitHub, URLs, debug logs, analytics, response errors or test screenshots. Encrypt transport in production design; constrain service credentials to least privilege; log opaque IDs, time, component and safe outcome codes. Define retention/deletion and backup behavior before real deployment; none is approved by Unit 3 documents.

### 2.1 Interface error vocabulary proposed for Hanlin

Use stable, typed error responses carrying a correlation ID but no internal stack or provider text. Hanlin must approve exact field names, HTTP mappings and retry semantics before final specification. Candidate errors: validation_error (400/422), unauthenticated (401), forbidden (403), not_found (404 with non-disclosure rules), insufficient_evidence (safe answer status, **not necessarily HTTP error**), conflict_idempotency_key (409), rate_limited (429 + bounded retry guidance), provider_timeout/dependency_unavailable (503/504 as appropriate), and save_outcome_unknown (retry/status lookup). Never expose unsanitized provider error details; do not retry non-idempotent operations without the same stable key.

## 3. Planned verification scenarios — **none executed**

| ID | Requirement | Scenario and expected result | Method / coordinating owner |
| --- | --- | --- | --- |
| V01 | R1 | Authorized supported inquiry yields permitted retrieved passage and validated source ID/version | C/M/E; Collins + Hanlin |
| V02 | R1/R2 | Unsupported query yields an honest limitation and customer-initiated agent option, no invented answer | C/M/E; Collins + David |
| V03 | R1/R5 | Stale, missing, or other-tenant source ID is rejected before display | M/E; David + Collins |
| V04 | R1/R6 | Hostile source text instructing model to ignore policies, change roles or exfiltrate data is handled as untrusted text | M/E; David + Collins |
| V05 | R1 | Empty, oversized, malformed, HTML/script or SQL-bearing input is validated and safely rendered; no injection or unauthorized provider call | C/M; Hanlin + David |
| V06 | R2 | User reviews and explicitly confirms escalation; only durably saved record produces acknowledgement and stable request ID | C/M/E; Collins + Hanlin |
| V07 | R2 | Repeated identical tenant/customer/idempotency-key/payload creates exactly one persistent escalation and returns original ID | M/E; David + Hanlin |
| V08 | R2 | Same idempotency key with different payload yields safe conflict, no second record or data leak | C/M; David + Hanlin |
| V09 | R2 | DB save fails or commit status unknown: no false acknowledgement; question preserved; safe lookup/retry | M/E; Collins + David |
| V10 | R2/R5 | Customer calls agent-only API or changes target customer/request ID: denied with no record disclosure | C/M/E; Hanlin + David |
| V11 | R3 | Feedback ties to source/answer/model versions; only approved reviewers can enact revisions | C/M; Collins + David |
| V12 | R3 | Evaluated update regresses fixed quality dataset: change rejected or rollback restores last approved version | M/E; Collins + David |
| V13 | R5 | Authorized customer-data adapter returns only allowlisted fields from synthetic customer record | C/M; Hanlin + David |
| V14 | R5 | Cross-customer or cross-tenant lookup denied despite valid login and modified IDs | M/E; Hanlin + David |
| V15 | R5 | Customer database timeout, malformed response or unavailable dependency produces bounded safe degradation, no fabricated data | M/E; Hanlin + Vlad |
| V16 | R1/R2/R4 | AI timeout, provider quota/429, malformed provider response: controlled fallback, original question retained, no raw errors/secrets | M/E; Collins + David |
| V17 | R6 | Every diagram arrow has named C1–C7 contract, source, destination, authorization context and failure path | I/C; David + team |
| V18 | R6 | Junior developer can use synthetic fixtures/mock provider and documented setup to reproduce focused component tests | I/M; Vlad + David |
| V19 | R5/R6 | Git diff and final export contain no tokens, passwords, private customer data or test secrets | I/secret-scan when available; David + team |
| V20 | R4 | Proposed 10,000 active sessions with selected request mix have documented quotas, resources, deployment and result metrics | I/L later; Vlad + David |
| V21 | R4 | Bounded 2x burst causes safe 429/503/backpressure, not unbounded queue growth | M/L later; Vlad + Hanlin |
| V22 | R4 | Provider capacity well below inbound demand triggers bounded admission, honest customer fallback, no quota overrun | M/L later; Collins + David |
| V23 | R2/R4 | Node/session restart does not lose committed requests, leak customer context or create duplicate tickets | M/L later; Vlad + David |
| V24 | R4 | Provider/DB service recovery avoids retry storms and returns to normal without false acknowledgements | M/L later; Vlad + Collins |
| V25 | R4 | Mocked-provider load and limited real-provider smoke reported as separate evidence, neither falsely implying full-scale capacity | I/L later; David + team |

**Early B12 answer-quality gate (not a production SLA):** fixed 20 questions = 12 supported, 4 unsupported and 4 ambiguous/misleading. At least 10/12 supported answers must match the actual source passages and all 4 unsupported must trigger fallback; inspect ambiguous cases individually. Record question set/version, prompt/model/retrieval configuration, reviewer judgments, and ten sequential response measurements including each latency, median, maximum, model, hardware/network environment and error/timeouts. No B12 demo score demonstrates R4 scalability.

## 4. 10,000-customer capacity **design and future validation**

### 4.1 Workload definition and illustrative sizing

Working interpretation (**not yet team-approved**): **10,000 concurrent connected/authenticated customer sessions**, not 10,000 simultaneous active AI completions. The load depends on inquiry frequency, retrieval volume, customer-data lookups, feedback and escalation. Vlad's first-session scenarios use five seconds solely as an **illustrative mean response-time assumption**, not a tested result or acceptance threshold.

| Scenario | Inquiry per customer | Inquiry rate at 10,000 customers | In-flight work at illustrative 5-second mean |
| --- | --- | --- | --- |
| Light | 1 / 600 seconds | 16.7 inquiries/s | about 84 |
| Proposed baseline | 1 / 300 seconds | 33.3 inquiries/s | about 167 |
| Busy | 1 / 60 seconds | 166.7 inquiries/s | about 834 |

Illustrative in-flight estimate = arrival rate × mean service/response time (Little's Law; valid for stable steady-state conditions). **33.3 inquiries/s is about 2,000 incoming inquiries/minute**. If every inquiry invokes an external model, the provider must accommodate that order of demand, or the architecture must explicitly limit/reject/route overload. Do **not** assume third-party quotas, caching, agent capacity or response time suffice. A separate 10,000-**simultaneous-requests** scenario remains open for clarification.

**Design decisions needed from Vlad/team:** choose session meaning, accepted baseline/busy request mix, inquiry interval distribution, payload/document sizes, model-call fraction, customer-data lookup frequency, escalation/feedback rates, burst multiplier and duration, provider quota and budget, login/session design, environment and resource bounds. Establish measurable p95/p99, throughput, error, queue-wait, availability and recovery gates **before** executing a test; no invented passing thresholds here.

### 4.2 Architecture constraints to review

The local Flask+SQLite prototype remains a valid educational demo but is not proof of production throughput or safe high-write concurrency. For the new production **design**, Vlad must identify: frontend ingress/admission control, replication or deployment shape, stateless/shared customer sessions, suitably durable shared escalation storage, customer-data isolation, model gateway with bounded concurrency/deadlines, human-agent workflow capacity, metrics/logging and outage handling. A modular application and deployed services are competing options; no production database/provider is approved by this verification plan. Keep AI logic separate from deterministic auth, database access and escalation. Explicitly show which resources scale independently and which are constrained by quotas.

### 4.3 Staged validation — **proposal only, no large load authorized**

| Phase | Synthetic traffic proposal | Dependencies | Gate / evidence |
| --- | --- | --- | --- |
| A: smoke | 1–10 clients; answer, unsupported, retries, roles | Mock provider + synthetic DB | Validate C1–C7, source IDs, denial and single-save |
| B: baseline | 100 then 1,000 sessions; ~5 minutes each | Mock provider + synthetic DB | p50/p95/p99, throughput, CPU/RAM, rate and errors |
| C: capacity | Ramp to 5,000 then 10,000 sessions; 10–15 minutes at agreed workload | Mock provider + synthetic DB | Stable throughput, session count, queue trends and correctness |
| D: burst | Up to 2× chosen arrival rate for 2 minutes, within agreed limit | Mock provider + synthetic DB | 429/503/backpressure, no resource runaway or duplicate saves |
| E: recovery | Simulate provider 429/timeout, customer DB delay and node restart | Mock failures | Recover safely; never acknowledge unsaved escalation |
| F: external API smoke | Small sample only **after** team/provider approval and quota/cost check | Selected live provider, fictional data only | Compatibility, citation checks, observed timeouts; **not full 10k capacity evidence** |

Suggested tooling, subject to team approval: reproducible Locust or k6 script and versioned synthetic fixtures. Record deployment shape, available CPU/RAM, connection pools, DB/index size, per-customer think time, traffic mix and durations. Measure offered vs accepted throughput, active sessions, p50/p95/p99 latency per endpoint, completion/error/timeout counts, 429/503, request in-flight count, queue depth, provider concurrency, persistence success/latency, resource use and time to recovery. **Never** execute substantial third-party traffic, deploy paid services or connect actual customer data without explicit approval.

Non-negotiable correctness criteria for eventual tests: zero cross-customer disclosures in the sampled scenarios; no false success acknowledgement for a failed/unconfirmed save; no duplicate escalation for a repeated scoped idempotency key; no fabricated source citations. Quantitative latency/throughput/availability targets remain open team decisions. Mocked-provider throughput validates **only the modeled application boundary**, not real provider quota, cost, production storage or full system capability.

**Overload behavior:** apply per-customer rate limits and global admission control, independently cap AI concurrency and queue length, return typed safe 429/503 with bounded retry guidance, and prioritize correct escalation state. Avoid retry storms and never treat an unlimited support queue as the fallback for unlimited model demand. If the database is unavailable, display unsaved/unknown state honestly and preserve the user's question for later retry.

## 5. Cross-section design review and gap register

The current published architecture, interface and AI files are **working frameworks**, not finalized detailed design. These are **risks/questions to resolve**, not asserted implementation defects. Confirm each against the reviewed pull request and exact commit.

| Finding | Severity | Scope / risk if absent | Responsible owner | Proposed verification / resolution | Status |
| --- | --- | --- | --- | --- | --- |
| F01 | High | Session definition, resource/storage model and 10k performance thresholds remain unchosen | Vlad + David | Approve workload mix, deployment/DB alternatives, test boundaries in decisions.md | **Open — team decision** |
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
| X01 | C1 question/answer points to C2 source IDs, C3 provider adapter and supported/unsupported paths in diagram | Pending teammates' detailed drafts |
| X02 | C4 confirmed escalation -> durable save -> ack -> C5 agent view, including duplicate/unknown commit | Pending |
| X03 | C7 customer adapter shows trusted customer identity, minimal fields, denied access and outage path | Pending |
| X04 | C6 feedback identifies answer/version, reviewer gate, regression and rollback | Pending |
| X05 | 400/401/403/404/409/429/503/timeout labels and response structures agree across diagram/flows/contracts | Pending |
| X06 | R4 session/rate and deploy/storage plan are selected and prototype/production clearly distinguished | Pending decision |
| X07 | Rationale defends actual module boundaries, coupling/cohesion and major tradeoff with authoritative citation | Pending Vlad's final 500 words |
| X08 | Correlation ID, source ID/version, escalation ID and idempotency key are distinct and scoped | Pending |

**Reviewer rule:** mark an item “verified” only after reviewing the exact PR/commit and linking the evidence. If a finding remains open, record an owner, impact, mitigation and team acceptance rather than pretending it disappeared.

## 6. Team milestones, contribution evidence and final-release gate

- **October 31 by 6 p.m. ET:** submit this drafted section from a focused branch and PR referencing Issue #14; ask Vlad for review. Report capacity and contract assumptions needing cross-team decisions.
- **November 1:** compare Vlad's diagram and Hanlin's C1–C7 with Collins's detailed flows; log X01–X08 outcomes and specific corrective PR comments. Avoid approval without completed review.
- **November 2:** resolve findings or document explicit acceptance; contribute concise reliability/coupling text to Vlad's ~500-word rationale; confirm exact reviewed commit and record actual contribution/reviewer evidence.
- **November 3 by 11:59 p.m. ET:** verify the integrated diagram, interface tables, 500-word rationale/reference and legible export; ensure LEO submission instructions and individual obligations are confirmed. Vlad coordinates final submission; no submission is claimed here.

**Design-review exit criteria:** all R1–R6 have traceable design evidence or an accepted gap; high-severity findings resolved/explicitly accepted; C1–C7 identifiers/flows/diagram consistent; privacy and durable escalation semantics documented; capacity remains labeled **design target**; one teammate reviewed the PR; team contributions and final approvals cite real evidence; the final specification contains the **three required** deliverables and a correctly counted 500-word rationale. Do not close #14 solely because the draft exists.

| Date | Check(s) | PR/commit reviewed | Evidence link | Observed result | Reviewer |
| --- | --- | --- | --- | --- | --- |
| Pending | X01–X08 | Pending | Pending | No cross-review completed yet | Pending |
| Pending | V01–V25 | Not yet implemented/executed | None | **No test results available** | Pending |

## 7. Sources and disclosure

- Team sources: [R1–R6 requirements](assignment-requirements.md), [Vlad's capacity options](architect-first-session.md), [C1–C7 framework](interface-contracts.md), [AI workflow framework](ai-integration.md), [backlog map](../backlog/implementation-map.md), [Issue #14](https://github.com/vlad8110/deskguide/issues/14), and [Issue #8 privacy](https://github.com/vlad8110/deskguide/issues/8).
- OWASP. (2023). *API Security Top 10: API1 Broken Object Level Authorization*. https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ — object-level authorization.
- NIST. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. https://doi.org/10.6028/NIST.AI.100-1 — AI risk evaluation, governance and oversight.
- Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. *Communications of the ACM, 15*(12), 1053–1058. https://doi.org/10.1145/361598.361623 — modular abstraction and change isolation.

**AI-assisted drafting disclosure:** this draft was produced with AI writing assistance for David's review. The named student should validate accuracy, revise as needed and follow the instructor's attribution rules before submitting. It does not establish personal approval, test execution or peer review.
