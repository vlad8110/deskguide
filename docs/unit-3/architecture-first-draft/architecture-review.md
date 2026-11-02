# DeskGuide Unit 3 — Architecture Review Draft

*November 1 shared-source snapshot. Current direction: [November 2 proposed decisions](../proposed-decisions.md).*

Vladimyr Merci | CMSC 495 Team 4 | November 1, 2026

Proposed architecture for team review. The design, interface contracts and rationale remain pending final team agreement.

## Working materials

Use this Google Doc and the shared draw.io file for architecture recommendations and corrections.

[Open the shared diagram in draw.io](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO)

[Open the diagram file in Google Drive](https://drive.google.com/file/d/1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO/view?usp=sharing)

[GitHub Unit 3 coordination hub](https://github.com/vlad8110/deskguide/tree/main/docs/unit-3)

[Week 3 delivery schedule](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/week-3-delivery-schedule.md)

[Vlad: architecture and coordination responsibility](https://github.com/vlad8110/deskguide/issues/11)

[Refined backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-eight-week-backlog-v2.md)

[Refined four-week sprint backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-four-week-sprint-backlog.md)

[Design Decisions and Review Log](https://github.com/vlad8110/deskguide/blob/docs/unit-3-architecture-review/docs/unit-3/design-decisions-and-review-log.md)

## Unit 3 — DeskGuide scope statement

### Scope statement

For Unit 3, I am designing DeskGuide as a customer-service platform that supports 10,000 concurrent customer sessions. Customers will ask basic service questions through an AI chatbot and receive answers grounded in approved knowledge documents, with links to the supporting sources. When the available evidence cannot support an answer, the question is too complex, or the AI service fails, DeskGuide will explain the limitation and offer a handoff to a human agent. Customers will review the information shared with the agent, and the system will acknowledge a support request only after it has been saved.

The design will integrate with an existing customer database through an authorized interface that limits access to the information needed for the inquiry. Customer, support-agent, and administrator permissions will be defined separately so customers cannot access other customers’ records or invoke restricted operations. Feedback and recurring interaction patterns will inform improvements through a reviewed process: identify a problem, propose a knowledge or answering change, evaluate it, and release a version that can be rolled back.

My architecture draft will show the system’s responsibilities, component boundaries, directional data flows, external connections, and capacity assumptions. I will keep those responsibilities clear enough for junior developers to understand and maintain. Hanlin’s interface contracts, Collins’s AI integration flows, and David’s verification plan will be checked against the same design.

### Behavior the architecture must cover

| Requirement | Scope for this draft | Backlog continuity |
| --- | --- | --- |
| Basic inquiries and supported answers | Retrieve permitted passages; return an answer with resolvable source references | B02, B07, B08, B10 |
| Complex, unsupported, or failed inquiries | Preserve the question; offer a customer-reviewed support request; save once despite retries; acknowledge the durable result; route to an authorized agent | B11, B13; B17 remains consolidated into B11 |
| Existing customer database | Define the authorized data boundary, minimum fields needed, and behavior when data is unavailable | Production design addition P02; preserve B04/B09 authorization principles |
| Learning from interaction patterns | Review permitted feedback/patterns and evaluate versioned improvements; define access and retention | B13/B16 plus production design addition P04 |
| 10,000 concurrent customers | Use the highest previously proposed workload and document the resulting demand | Production design addition P01; preserve B05/B12 measurement requirements |
| Maintainability | Give components focused responsibilities, explicit contracts, and understandable failure behavior | B03, B04, B19 |

### Boundaries for Unit 3

This is a system design specification. The first draft does not include application implementation, a live deployment, actual customer-database access, or measured proof of 10,000-customer capacity. Examples and any later local demonstrations will use fictional documents and synthetic customer data.

Proposed production design: one modular Flask application replicated behind HTTPS ingress, with shared PostgreSQL state. Improvements require review, evaluation, versioning and an approved release. Automatic second-provider failover remains deferred. Provider capacity, hosting and deployment sizing remain pending.

The original employee-support prototype remains the backlog baseline. This Unit 3 draft extends that baseline to the customer-service requirements without claiming the earlier Flask/SQLite prototype already satisfies production capacity.

### Working dates

Internal combined review: November 1; corrections and agreement: November 2. Working submission deadline: November 3, 2026, at 11:59 p.m. Eastern.

### Source basis

- [Unit 3 assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

- [Refined eight-week backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-eight-week-backlog-v2.md)

- [Refined four-week sprint backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-four-week-sprint-backlog.md)

- [Current assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

The source backlog’s prototype estimates remain historical. Additional production-design work must be estimated separately.

## Unit 3 — Selected workload assumptions

### Selected scenario

Planning assumption: 10,000 active customer sessions, each submitting one new inquiry per minute on average. This implies approximately 166.67 inquiries per second. The assignment specifies concurrency; this arrival rate is our proposed workload assumption, not measured usage or demonstrated capacity.

A concurrent session means a customer is using the service during the same period as the other customers. It does not by itself specify a persistent network connection or mean all 10,000 customers submit at the same instant. This baseline assumes inquiries are distributed over the minute; synchronized demand is considered separately below.

### Baseline demand

| Quantity | Calculation | Design demand |
| --- | --- | --- |
| Concurrent customer sessions | Selected scope | 10,000 |
| New inquiries per customer | Selected busiest scenario | 1 per minute |
| New inquiries per minute | 10,000 × 1 | 10,000 |
| Average new inquiries per second | 10,000 ÷ 60 | 166.67, approximately 167 |
| New inquiries in one hour at this sustained rate | 10,000 × 60 | 600,000 |

Calculations below use the unrounded rate, 10,000 ÷ 60. The 167 figure is a rounded description, not an extra capacity allowance. This rate counts new customer inquiries only; retries, citation clicks, authentication, feedback, agent actions, database calls, and health checks add separate work.

### Simultaneous work depends on response time

For a stable workload, average in-flight inquiries can be estimated as average arrival rate multiplied by average end-to-end time. The following times illustrate the effect; none is an agreed response-time target or measured result.

| Illustrative mean end-to-end time | Calculation | Estimated average in-flight inquiries, rounded up |
| --- | --- | --- |
| 5 seconds | (10,000 ÷ 60) × 5 | 834 |
| 10 seconds | (10,000 ÷ 60) × 10 | 1,667 |
| 15 seconds | (10,000 ÷ 60) × 15 | 2,500 |

These averages do not size a queue, predict peak concurrency, or establish a safe server count. A system that receives work faster than it can finish it will accumulate waiting work; a stable-average calculation does not prove it can sustain the arrival rate.

### AI-service demand assumption

For the worst-case planning scenario, every new inquiry requires one generation call: approximately 166.67 calls per second, 10,000 per minute or 600,000 per hour. Caching is not credited toward capacity. Additional model calls would increase demand.

Collins will identify the exact provider/model, account request and token quotas, concurrent-call limits, permitted use and prompt/response sizes. Cohere remains the first prototype candidate, with Groq as a comparison; production capacity requires separate evidence.

### Separate synchronized stress scenario

Proposed simulated load scenarios: approximately 166.67 inquiries/second steady state; 333.33 inquiries/second for two minutes; and a separate burst of 10,000 arrivals within one second. These scenarios use controlled substitutes before any permitted live-provider test.

Use bounded admission without an AI waiting queue. When capacity is unavailable, return a safe busy response and preserve the question. Keep support-request admission separate and bounded; agent work is not unlimited. Replica counts, in-flight limits and support capacity require measured sizing.

### Decisions still needed before sizing or validation

| Decision | Who helps resolve it | Why it matters |
| --- | --- | --- |
| Response-time, error-rate, timeout, and recovery targets | Vlad + David; Collins checks provider behavior | Defines acceptable service, rather than inferring it from illustrative averages |
| Prompt/answer sizes, inquiry mix, and number of external calls | Collins + Hanlin | Determines token demand, payloads, and dependency traffic |
| Customer-data lookup and escalation/feedback rates | Vlad + Hanlin + Collins | Determines database and agent-workflow demand |
| Queue bounds, admission limits, safe retries, and overload response | Vlad + Hanlin + Collins; David reviews | Prevents uncontrolled waiting and duplicate work |
| Production storage, replication, and deployment choices | Vlad; David reviews assumptions | Must follow measured capacity or justified estimates, not a guessed server count |
| Burst profile, test duration, environment, and provider allowances | David + Vlad + Collins | Makes the validation reproducible and distinguishes mocked from real dependencies |

Proposed production service level: at least 95% of all eligible inquiries receive a supported AI answer within 15 seconds. Eligibility means a valid, authorized, in-scope inquiry with supporting evidence assigned to the AI route before admission. Busy responses, timeouts, invalid answers and unnecessary fallback count as misses. Explicit human requests and genuinely unsupported questions are reported separately. Apply a 20-second end-to-end deadline and a provider timeout no longer than 12 seconds or the remaining budget, whichever is shorter. These are targets awaiting capacity evidence.

## Architecture diagram

[Edit the live diagram in draw.io](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO)

![DeskGuide component architecture](deskguide-unit-3-architecture.png)

Figure 1. Proposed component architecture. M1–M9 are logical modules.

### Proposed production deployment

![DeskGuide proposed production deployment](deskguide-unit-3-production-deployment.png)

Figure 2. Proposed deployment with replicated application instances and shared durable state.

## Unit 3 — Component responsibilities

Production proposal: HTTPS ingress/load balancing distributes requests across modular Flask replicas using production WSGI. Shared PostgreSQL holds durable application state through M9. The existing customer database remains a separate read-only dependency. Hosting, replica counts, database sizing and provider capacity remain pending.

### Component proposal

I propose separating DeskGuide into the following logical components. Each component has one main responsibility and communicates through a defined interface. These boundaries will guide the architecture diagram and the team's contracts.

| ID | Component | Main responsibility | Information and interactions | Backlog / contract alignment |
| --- | --- | --- | --- | --- |
| M1 | Browser interfaces | Present customer questions/results, human-agent work, and authorized administration | Sends customer, agent and administrator actions to M2; displays authorized results, source links and controlled failure states. Uses server-issued submission IDs and shows acknowledgement only after durable commit. | B03/B08/B13/B14; C1/C4/C5/C6/C8 |
| M2 | Application and access control | Validate requests, enforce permissions and customer scope, and coordinate use cases | Derives trusted C9 access context from the server-validated session; enforces role, customer and record scope before protected operations. Uses bounded admission, correlation IDs and CSRF checks for state-changing browser requests. | B04/B06/B09; C9 access context across protected C1–C10 operations |
| M3 | Knowledge and retrieval | Manage approved knowledge versions and retrieve only passages the caller may access | Returns approved passages with stable document, section and version identifiers. C8 restricts document administration to authorized administrators. Approved source changes from M8 enter through this boundary. | B02/B07/B14; C2 retrieval; C8 document administration |
| M4 | AI provider adapter | Isolate external generation and provider-specific failure behavior | Sends only the permitted question and retrieved passages to the external provider. Keeps credentials server-side; excludes internal C9 context and customer-database fields. Applies a provider timeout of at most 12 seconds within the 20-second inquiry deadline, with no automatic generation retry. Coordinates shared breaker state through M9. Proposed breaker: three qualifying failures within 60 seconds, then a 30-second cooldown and one global half-open trial protected by a 20-second lease per provider/model/credential scope. Counter/reset and write policy remain with Collins. | B05/B10/B11; C3 |
| M5 | Answer and source validation | Validate candidate structure, authorized citations and evidence under C10 | Checks structure, source membership, document/section versions, access and resolvability. Collins must define the executable runtime evidence-support rule and its limits in C10. Valid citations alone do not prove semantic correctness. B12 manual scoring remains an offline verification activity. | B07/B10 runtime checks; C10 validation; B12 offline manual evaluation |
| M6 | Escalation and agent workflow | Manage the durable customer-to-human handoff | Issues and registers submission IDs before confirmation; binds each ID to the customer and operation. Atomically saves confirmed content and a replay receipt through M9. Enforces ownership and state transitions. Acknowledges only committed results and distinguishes failed from uncertain saves. | B11/B13; C4/C5; B17 remains consolidated into B11 |
| M7 | Customer-data adapter | Limit access to the existing customer database through a stable boundary | Provides a read-only, authorized lookup of customer_id and account_status for the initial account-status use case. Returns a deterministic application response without model generation. General questions need no lookup. Customer-database fields are not sent to the AI provider. | Production addition P02; B04/B09; C7 |
| M8 | Feedback and reviewed improvement | Turn permitted feedback/patterns into evaluated, controlled improvements | Accepts permitted feedback linked to the inquiry, including fallback outcomes without an answer. Reviewers evaluate proposed changes; approved source updates use M3/C8 and approved generation configuration uses M4. Vlad coordinates release/rollback approval. No automatic training or unrestricted conversation retention is assumed. | B13/B16; production addition P04; C6 |
| M9 | Persistence adapters | Provide durable storage through component-owned data interfaces | Proposed shared PostgreSQL storage covers approved knowledge, support requests and replay receipts, permitted feedback, sessions and shared breaker records/leases. Business components own their records and rules; other modules use their interfaces. Raw conversation retention requires a separate decision. | B06/B11/B13; durable interfaces for knowledge, support, feedback, sessions and shared breaker state |

### Backlog and Unit 3 scope

These nine responsibilities are derived from the team backlog with Unit 3 design additions. M7 customer-database integration is a Unit 3 addition. M6 agent assignment/states, M8 governed improvement/versioning, and production admission/isolation policies extend the prototype backlog. B13/B14 feedback, request review and document administration are later full-backlog items, outside the four-week B01–B12 extract. These additions do not by themselves create new team implementation commitments.

### External boundaries

The external AI provider and existing customer database sit outside the application boundary. Browsers are untrusted. Proposed authentication uses opaque server-side sessions in Secure, HttpOnly, SameSite=Lax cookies, with CSRF protection on state-changing requests. Every protected action checks role and record scope. Idle/absolute expiry, logout scope and identity provisioning remain to be specified.

M9 provides component-owned persistence interfaces over proposed shared PostgreSQL. M3, M6 and M8 retain control of their data rules. Application replicas share session, receipt and breaker state; the existing customer database stays separate and read-only.

M2 supplies verified C9 access context to protected internal operations and a correlation ID for safe diagnosis. Browser-provided identity/role fields are not authority. C9 credentials/context are not sent to the external model. Document administration does not grant customer-support access. Operational logs avoid unnecessary raw questions and customer data.

Source-ID and access checks are structural checks. Whether a passage actually supports an answer needs a separate evaluation policy and review; valid links alone do not guarantee factual correctness.

### Boundaries to settle with the team

| Person | First review needed |
| --- | --- |
| Vlad | Confirm the service-level denominator, deployment proposal and cross-component boundaries; reconcile diagram, contracts and rationale for one final team review. |
| Hanlin | Align C1–C10 schemas, authorization and errors. Specify session expiry/logout/provisioning, server-issued submission-ID registration and expiry, ownership/version conflicts and atomic persistence contracts. |
| Collins | Provide provider/model quota evidence, allowed AI input/output, executable C10 evidence checks, and the shared-breaker counter/reset/write policy. |
| David | Verify denominator-aware service-level tests, expired/unknown ID and duplicate races, session/ownership isolation, and shared-breaker concurrency/recovery across replicas. |

### Implications of the selected workload

M1–M9 are logical modules, not nine services. The production proposal replicates one modular Flask application behind a load balancer and uses shared PostgreSQL state. Bounded AI admission avoids an application waiting queue. The proposed service level is 95% of eligible inquiries answered within 15 seconds, with a 20-second deadline. Provider, replica/database sizing and support limits require evidence.

## Unit 3 — Customer question walkthroughs

These two walkthroughs turn the component responsibilities into interactions for the architecture diagram. They describe intended behavior, not implemented or tested results. The workload remains 10,000 concurrent customer sessions at about 167 new inquiries per second.

### Backlog boundary

The supported-answer flow follows B04/B07/B08/B09/B10. The fallback and single-save behavior follows B11, including the failure handling consolidated from B17. B12's manual evaluation of answer support and response time remains a separate verification activity. B13 adds saved feedback and restricted administrator request review later in the full backlog; it is outside the B01–B12 four-week extract.

Customer-specific authorization, an existing customer-database adapter, and agent assignment/status details are proposed Unit 3 design additions. These walkthroughs do not present them as previously approved implementation commitments.

### Walkthrough A — A question with available supporting sources

Illustrative question: “Where can I find the customer portal setup instructions?” Assume an approved fictional guide exists for the example. This does not assert that the document or evaluation case has already been created.

Expected outcome: the customer sees an answer with working, authorized source references. A valid source link is not a guarantee that the answer is factually supported; B12 separately evaluates that quality.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| A1 | M1 Browser interfaces → M2 Application/access control | Submit the question using the authenticated session cookie and the server-associated inquiry/correlation ID. Show pending status. Hanlin will finalize field names and size limits. | Empty/oversized input receives validation feedback. Keep editable question text in the current form. |
| A2 | M2 Application/access control | Validate input and the session, derive C9 role/customer/document scope, assign a server correlation ID and determine routing before applying bounded admission. | Deny unauthorized access. If admission/dependency capacity is unavailable, return a controlled status and preserve the question; do not wait indefinitely. |
| A3 | M2 → M3 Knowledge/retrieval; M3 → M9 storage interfaces as needed | Pass the question and trusted permitted-source scope. Retrieve approved passages with stable document, section and version identifiers. Return the permitted passage set to M2. | If no relevant permitted evidence is available, use Walkthrough B without calling the model to invent an answer. Retrieval failure is reported as unavailability, not as proof that no source exists. |
| A4 | M2 → M4 AI provider adapter → external AI provider | Send only the permitted question and retrieved passages with their identifiers. Retain internal C9 context and database fields inside DeskGuide. Bound the provider call to at most 12 seconds and the remaining 20-second inquiry budget. | On timeout, quota failure, malformed output or open circuit, follow Walkthrough B without an automatic generation retry or second-provider failover. |
| A5 | External provider → M4 → M2 | Return a structured candidate answer and source identifiers associated with the same inquiry. | A result arriving after timeout/cancellation is obsolete and must not overwrite the current fallback view or create a support request. |
| A6 | M2 → M5 Answer/source validation, with M3 resolving source references | Use C10 to check structure, source membership, versions, access and resolvability, then apply the agreed runtime evidence-support rule. Return a validated result or controlled invalid/unsupported outcome. | Reject unknown, inaccessible or unresolvable citations. Collins must specify the executable evidence-support rule; structural checks alone do not establish semantic correctness. B12 evaluates support separately. |
| A7 | M2 → M1 Browser interfaces | Return the result that passed the agreed runtime validation policy, its authorized source references and the matching inquiry ID. Display citations beside the answer. | A disconnected browser must not cause an unrelated or stale result to replace a newer inquiry. No general conversation-history persistence is assumed. |
| A8 | M1 → M2 → M3 when a source is opened | Recheck access to the selected document/section/version and return the authorized source content. | If access changed or the source cannot be resolved, show a clear unavailable/denied result rather than another customer's content or a silently substituted passage. |

Main diagram path: M1 → M2 → M3 → M2 → M4/external AI → M2 → M5 → M2 → M1. M3 uses its M9 storage interface where needed. The return to M2 denotes orchestration, not a requirement to deploy every component separately.

Customer-data boundary: this general question needs no lookup. The initial customer-specific case is a read-only account-status lookup through M7 using customer_id/account_status and trusted scope. M2 returns that status deterministically without AI generation. Customer-database fields are not sent to the external model.

### Walkthrough B — Unsupported/complex inquiry or AI failure, followed by a support request

Entry conditions: no permitted supporting passages; an explicit request for a person or an agreed complexity-routing rule; invalid citations/output; or retrieval/provider timeout, quota or service failure. Keep “insufficient evidence” distinct from “service unavailable.” Complexity and evidence-sufficiency policies are still proposed design decisions.

Expected outcome: the customer receives a clear limitation and can choose to create one durable support request. A saved-request acknowledgement means storage succeeded; it does not mean an agent accepted or resolved the request.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| B1 | M2 Application/access control → M1 Browser interfaces | Return a safe limitation/unavailability reason and the support-request option. Retain the original question in the current editable form. | Hide credentials, raw provider errors and unnecessary internal details. Keeping text in this form does not promise survival across a page reload. |
| B2 | Customer through M1 | When the support form opens, the server issues and registers an unused submission ID bound to the customer and operation. The customer reviews/edits the content and explicitly confirms or cancels. | Registration alone creates no human-visible support request. Unused IDs expire after the agreed validity period. A deliberate new request receives a newly issued server ID; retries do not automatically obtain a replacement. |
| B3 | M1 → M2 → M6 Escalation/agent workflow | Submit confirmed content and the registered ID. Revalidate session, customer/operation scope, content and unused-ID validity. Enforce deduplication on the server; disabling the button is only a usability measure. | Reject expired/unknown IDs or unauthorized input with a controlled response. Preserve editable content. Do not recreate an expired request by silently generating a new ID. |
| B4 | M6 → M9 persistence interface | In one transaction, atomically create the support request and its completed receipt under the unique customer/operation/submission identity. Bind the receipt to the confirmed payload so repeats can return the committed result. | If the transaction is known to have failed without saving, report “not saved.” If its outcome is uncertain, report “confirmation unavailable” and resolve using the same identity; do not assert that no record exists. |
| B5 | M9 → M6 → M2 → M1 | After durable commit, return the saved request ID and acknowledgement. | If commit succeeds but acknowledgement is lost, replaying the same authorized ID/payload returns its completed receipt and existing request. Retain completed receipts for the request lifetime and 30 days after resolution. |
| B6 | M2/M6 on retry | Check the registered ID, authorized customer/operation scope, payload match and completed receipt before deciding whether to create, replay or reject. | Completed same-ID/same-content requests return the existing result; changed content conflicts. Unknown or expired unused IDs are rejected, never recreated. Cross-customer receipt lookup is denied. Only a deliberate new submission gets a fresh server-issued ID. |
| B7 | Agent interface M1 → M2 → M6 → M9 | A permitted human opens the saved-request list/detail. Enforce role and record scope on the server before returning content. | Restrict unauthorized requests. Document-administration rights alone do not grant access to customer conversations or support requests. |
| B8 | Agent interface → M2 → M6 → M9 | Proposed five states: queued → assigned → in_review → waiting_customer → in_review → resolved. Claim/assignment and transitions use atomic owner/version checks. The owner may release unfinished work to queued with a reason. | Resolved is terminal; late replies do not reopen it automatically. Only the assigned agent may change owned work within permitted transitions. Concurrent stale changes conflict. Customer replies to waiting_customer return work to in_review; exact contract enforcement needs team review. |

Main diagram path: fallback reason → M2 → M1/customer confirmation → M2 → M6 → M9 durable save → M6/M2 → M1 acknowledgement. The agent later follows M1 → M2 → M6 → M9 for permitted review and updates.

Capacity boundary: AI admission and support-request admission are separately bounded. Provider limits, database capacity and agent throughput constrain service. David will test the proposed load and recovery scenarios; numerical in-flight and support limits require sizing evidence.

### Verification and draft contracts

| Check | Expected design behavior / backlog basis |
| --- | --- |
| Supported question and source click | Stable authorized source IDs resolve; expected supporting passages and answer support are manually evaluated under B07/B12. |
| Missing evidence / explicit human request | No unsupported model answer is invented; routing follows the agreed policy; customer chooses whether to submit support. |
| Timeout, quota failure, service failure and malformed output | Controlled response with original question retained; no secret/raw error disclosure; B11 tests begin during integration. |
| Invalid or inaccessible citation | Reject the structural result; do not bypass source permissions. Semantic answer-quality evaluation remains manual under B12. |
| Confirm, cancel, repeat submit, changed content and lost acknowledgement | Cancel creates no support request. Registered IDs permit one atomic save; completed same-payload retries replay the receipt; changed content conflicts; unknown/expired unused IDs are rejected without recreation. Test concurrent duplicates and uncertain commits. |
| Customer/agent permissions and customer-data access | Deny unauthorized/cross-customer access; synthetic examples only. Agent/customer-data extensions are Unit 3 design work. |
| Provider response arriving late | Correlate inquiry results and suppress obsolete UI updates; never auto-save a support request because a provider returned late. |
| Workload and regression | Test the 95%/15-second service level over all eligible received inquiries, counting busy/failure outcomes as misses. Simulate steady 166.67/s, two-minute 333.33/s and separate 10,000-arrival/one-second bursts. B12 prototype checks do not establish production capacity. |

Contract mapping: C1 inquiry/result; C2 retrieval/sources; C3 generation; C4 support submission; C5 agent workflow; C6 feedback; C7 read-only customer lookup; C8 document administration; C9 verified access context; C10 runtime evidence/source validation. Hanlin will reconcile the final schemas and errors with this diagram and the review log.

### Items to settle before the architecture diagram is finalized

- Collins: define runtime evidence-support and complexity routing, provider/model quotas and breaker counter/reset/write policy.

- Hanlin: specify session expiry/logout/provisioning, registered-ID validity and receipt/ownership concurrency contracts.

- David: provide reproducible service-level/load, expired-ID/duplicate, session/ownership and multi-replica breaker verification.

- Vlad: reconcile cross-component findings, proposed deployment and final rationale, then obtain all four reviews of one final version.

## Team review

This architecture combines the current proposals for team review. Final agreement and LEO submission remain pending.

### What this review copy covers

- DeskGuide customer-service scope and relationship to the team's refined backlog.

- Selected workload: 10,000 concurrent customer sessions, each generating one inquiry per minute on average, approximately 167 new inquiries per second.

- Nine logical component responsibilities, with backlog-derived work and Unit 3 design additions distinguished.

- Supported-answer and unsupported/provider-failure-to-human-support walkthroughs.

- Editable visual architecture diagram and full-size image preview.

### Remaining architecture work

Production storage, deployment pattern, bounded admission and service targets are proposed above. Exact provider/model quotas, replica/database sizing, session lifetimes, unused submission-ID validity, payload/in-flight/support limits and capacity results remain pending.

M5 performs runtime evidence and source validation under C10. B12 manual scoring is separate offline verification. The executable runtime evidence-support rule remains with Collins; valid source IDs alone do not establish correctness.

The design rationale is available with the review log. Align its final wording with the agreed diagram and C1–C10 contracts.

### Requested team review

- Hanlin: finalize C1–C10, session/identity details, submission-ID registration/expiry and ownership/version conflicts.

- Collins: supply provider/model capacity evidence, runtime evidence-support policy and shared-breaker counter/reset/write details.

- David: verify the service-level denominator, expired-ID/duplicate races, session/ownership isolation and shared-breaker recovery.

- Vlad: reconcile the architecture, contracts and rationale, resolve cross-component findings and coordinate final team review.

B13/B14 are later full-backlog items rather than commitments in the first four-week extract. Customer-database integration, detailed agent workflow and governed improvement are Unit 3 design additions. Automatic second-provider failover remains deferred and B17 remains consolidated into B11.

### Dates

Internal combined review: Sunday, November 1; corrections and agreement: Monday, November 2. Working submission deadline: Tuesday, November 3, 2026, at 11:59 p.m. Eastern.
