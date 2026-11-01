# Unit 3 Design Decisions and Review Log

Coordinator: Vladimyr Merci, Lead Architect. Updated: November 1, 2026. Revision 3.

I have worked through the open architecture questions and collected my proposed solutions here. Please review the items assigned to your role, flag concerns, and provide the requested clarification or evidence. I will reconcile the replies before assembling the final specification.

**Status: Working proposals for team review.** The [500-word rationale draft](design-rationale.md) reflects these proposals.

## 1. Sources and inspected revisions

| Source | Revision inspected | Evidence supplied |
| --- | --- | --- |
| [Vlad's architecture, PR #15](https://github.com/vlad8110/deskguide/pull/15) | `eae4e92948df9bdbca36879bd111046bc35ce746`, before this update | Scope, selected workload, nine logical components, walkthroughs and shared sources |
| [Collins's integration flows, PR #16](https://github.com/vlad8110/deskguide/pull/16) | `bcf86e01b779436325c4956773cd91cffa7e8276` | Answering, failure, escalation, improvement and bounded-queue proposals |
| [Hanlin's contracts, PR #17](https://github.com/vlad8110/deskguide/pull/17) | `95875135e8940f4ec44e7b431c1c9c0504fccf55` | C1–C10, schemas, proposed values and open policies |
| [Collins's review of Hanlin's draft](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5725100910) | PR #17 revision above | Specific authorization-context, semantic-support, feedback and timeout questions; COMMENTED review, not approval |
| [David's verification package, PR #18](https://github.com/vlad8110/deskguide/pull/18) | `a9912c913e477b591bb801e48a5387a81b46104b` | Updated selected-workload and burst scenarios, security/reliability checks, and response to D01–D21 |
| [David's review of the proposals](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5725784156) | Review of `13b635fc743ef4f3cc9b1318adcfa0bdcb3a1405`, October 31 | Workload interpretation accepted; capacity, expiry, session, ownership, grounding and breaker details remain open |
| [Assignment requirements](assignment-requirements.md) | Course instructions linked there | Diagram, typed contracts, 500-word rationale; 10,000 concurrent users without a specified inquiry frequency or latency target |

The [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit) and [shared draw.io diagram](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO) remain the editable architecture review sources. GitHub holds this coordination log, section drafts and snapshots. The existing diagram is the first-draft snapshot and does not yet depict every proposal below.

## 2. Established direction and approval boundaries

| Item | Authority and current status |
| --- | --- |
| Scope | Vlad directed applying the customer-service scenario to DeskGuide, including 10,000 users and existing customer-data integration. Instructor clarification remains separate. |
| Workload | Vlad selected 10,000 active sessions averaging one inquiry/customer/minute. Selected assumption; capacity untested. |
| Roles and coordination | Vlad coordinates; Hanlin interfaces, Collins integration, David verification. Existing issues #11–#14. |
| Review format | Shared Doc/draw.io are editable architecture sources; GitHub coordinates; PNG for review, PDF for final submission. |
| First-draft review | Vlad reviewed the first architecture draft; team review remains pending. |
| Teammate draft reviews | Vlad plans to review PRs #16–#18 and consolidate findings. |
| David's response | Review received. David accepts the selected workload interpretation; final approval remains pending. |
| November 1 follow-up | I propose the D11 timely-AI-service target and D09/D17 server-issued submission IDs. Section owners provide the remaining rules and evidence. |

## 3. Recommendations and clarification

### D01 — Workload

**Raised by:** David XR01/verification §4; Hanlin V14–V16 depend on it. **Owner:** Vlad, reviewed by David.

Use the selected 10,000 active sessions × one inquiry/minute = 10,000/minute = 166.67/second (approximately 167). This does not require persistent connections or 10,000 simultaneous model calls. Retain 33.3/second as a lighter sensitivity case, not the baseline. Define traffic distribution, lookup/feedback/escalation fractions and extra endpoint work. At one model call/inquiry, demand is 600,000 calls/hour; document the actual call fraction. Worker sizing requires mean service times, resources and quotas, not a latency percentile alone.

**Evidence/status:** Selected workload interpretation accepted by David. Request mix, model-call fraction, provider capacity and resource sizing remain open.

### D02 — Existing customer database

**Raised by:** David XR05 and Hanlin C7. **Owners:** Vlad boundary, Hanlin contract, David isolation review.

Make C7 read-only, derive identity/scope server-side, authorize before lookup and return allowlisted fields. Keep the existing database separate from DeskGuide support/feedback storage; AI gets no direct database access. Account changes go to a human. D16 supplies a concrete minimum-data use case.

**Evidence/status:** Proposed. Hanlin provides authorized, denied and unavailable examples.

### D03 — Evidence sufficiency and semantic support

**Raised by:** Collins's PR #17 review, question 2/V19; David distinguished structural checks from semantic support. **Owners:** Collins policy, Hanlin C10, David evaluation.

Retrieve only permitted relevant passages. Clarify or offer support when evidence is missing, conflicting or inadequate. Require substantive claims to reference supporting passages. Check reference membership, version, permission, resolvability and quoted text against actual retrieved content; reject malformed or unsupported candidates. Valid IDs or matching quotations alone do not prove entailment.

**Evidence/status:** Proposed; the implementable pre-generation sufficiency and runtime semantic-support rules await Collins's examples and policy, with positive/negative cases and manual evaluation.

### D04 — Failures and acknowledgements

**Raised by:** Collins's review/failure flows and David's durable-save checks. **Owners:** Collins outcomes, Hanlin contracts, David failure review.

Use 200 with `temporarily_unavailable` for a successfully delivered controlled AI-unavailable outcome and support offer; it is not an AI-answer success. Use 429 for customer limits, 503 `SERVICE_BUSY` for aggregate admission overload and 504 `DEADLINE_EXCEEDED` when the overall deadline expires and a response is still deliverable. Bound provider waiting within that deadline; ignore late results. Initially use no automatic generation retry.

Known failed save means “not saved”; unknown commit means “confirmation unavailable,” followed by same-ID lookup/retry. Acknowledgement requires durable persistence. Preserve unsent text in the current view without promising reload persistence.

**Evidence/status:** Proposed; provide a complete outcome table, response examples and timeout/disconnect/lost-acknowledgement checks.

### D05 — Feedback without an answer

**Raised by:** Collins's PR #17 question 3: C6 requires `answer_id`, but some inquiries never create one. **Owners:** Hanlin C6, Collins flow, David access/expiry.

Require `inquiry_id`, rating and optional comment; verify inquiry ownership. Derive outcome/configuration from trusted metadata. Do not require an answer ID; retain a nullable internal link where an answer exists. Keep Hanlin's optional category if valid for the outcome. Pre-inquiry rejection creates no separate feedback feature.

**Evidence/status:** Proposed; provide examples for an answer and a failed inquiry, including metadata expiry under D09.

### D06 — Authorization context

**Raised by:** Collins's PR #17 question 1: C9's blanket first-argument rule conflicts with C3 `generate(request)`. **Owners:** Hanlin signatures, Collins outbound payload, David boundary review.

Protected application operations receive verified `AccessContext`. Keep `generate(request)` limited to sanitized generation data and a safe correlation ID; never serialize credentials, session tokens, roles or the internal authorization object to the provider. Revise “every internal method” instead of adding unused authority parameters to pure helpers.

**Evidence/status:** Proposed; reconcile signatures and show an allowed outbound payload and a forged-context denial example.

### D07 — Company/customer isolation

**Raised by:** Hanlin V20 and David's isolation questions. **Owners:** Vlad scope, Hanlin role matrix, David denial checks.

Use one company initially without mandatory multi-company tenancy. Customers see their own records; agents see the unassigned work queue and requests assigned to them. Document-administration rights alone grant no support access. Scope is server-derived and checked for each protected object operation.

**Evidence/status:** Proposed; provide role/operation and non-disclosure examples. Multi-company support is deferred rather than assumed.

### D08 — Improvement and release authority

**Raised by:** Collins's improvement flow and Hanlin's approver question. **Owners:** Collins walkthrough, Hanlin C6, David review, Vlad release coordination.

A contributor proposes a bounded source/retrieval/prompt/configuration change; a different qualified member reviews it; evaluation precedes release. Vlad coordinates authorization. Record versions, evaluation and rollback reference. Use the existing review workflow rather than build a separate approval application. No automatic retraining or release from ratings.

**Evidence/status:** Proposed; supply one complete improvement/rollback example.

### D09 — Retention and duplicate-protection lifetime

**Raised by:** Hanlin V11/V21 and David's privacy review. Durations are Vlad's proposed defaults. **Owners:** David retention/security, Hanlin expiry contracts, Collins feedback utility.

Do not persist general chat transcripts. Keep minimal inquiry metadata for 30 days from creation; linked feedback expires with it. Diagnostic logs last 7 days without raw question/answer/customer content, credentials or direct customer identifiers. Keep confirmed support content/replies while open plus 30 days after resolution. Periodically review old open work instead of deleting unresolved requests automatically. Use scheduled daily cleanup.

I propose server-issued submission IDs registered in PostgreSQL before use. Bind each ID to the authenticated customer and intended operation. Only a registered, unused, unexpired ID can create a request. Save the request and complete its receipt in one transaction, with a database uniqueness rule for concurrent retries. Store the result reference and a payload-comparison value without keeping another copy of the support text.

| Submission identity | Behavior |
| --- | --- |
| Registered, unused and unexpired | Save once and acknowledge after the durable commit |
| Completed, same payload | Return the original saved result; create nothing new |
| Completed, changed payload | Return a conflict |
| Expired unused ID or missing registration/receipt | Reject; offer status checking and a deliberate new submission |

Keep completed receipts for the retained request's lifetime; unused-ID expiry must not delete a completed receipt early. When a retained request and its receipt are purged, its old ID is unknown and remains unusable for creation. The browser must not automatically replace a failed retry with a fresh ID and resubmit. A deliberate new submission requires a newly issued ID and customer confirmation. This protects retries of the same submission; separately confirmed new submissions remain separate actions.

David should recommend the unused-ID expiry period and review receipt, purge, backup and audit retention. Hanlin should specify issuance, ownership, payload comparison, response examples and recovery. Evaluation/release records and provider copies need separate retention definitions.

**Evidence/status:** Server-issued, pre-registered IDs proposed by Vlad on November 1. Hanlin's current browser-generated UUID contract requires team review and revision; expiry values and deletion rules remain open.

### D10 — Deployment and storage

**Raised by:** David §4.2/XR02, asking how production differs from the local Flask/SQLite prototype. **Owner:** Vlad; David reviews bottlenecks.

Propose one modular Flask codebase, replicated behind HTTPS ingress/load balancing and a production WSGI server. Shared PostgreSQL holds durable DeskGuide records, server-side sessions and initial knowledge/version storage through component-owned adapters. M7 isolates the existing customer database. Keep SQLite locally. Initially avoid separate microservices, Kubernetes, Redis, a vector database and a broker.

This reduces separately deployed parts for junior developers while preserving interfaces. Replicas scale the whole application, not each logical module independently. Provider quotas, database connections and agent capacity remain constraints. [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/), [SQLite usage guidance](https://www.sqlite.org/whentouse.html) and [PostgreSQL concurrency documentation](https://www.postgresql.org/docs/current/mvcc.html) support evaluating these choices, not a capacity guarantee.

**Evidence/status:** Proposed. Vlad supplies deployment/state ownership and sizing reasoning. Hosting vendor, database version/size, replica count, availability topology and cost remain unselected.

### D11 — Performance and admission

**Raised by:** David's plan, Hanlin V4–V9/V14–V18 and Collins's queue proposal. Values are provisional, not measured.

| Setting | Proposal | Evidence/clarification owner |
| --- | --- | --- |
| Timely AI service | At least 95% of eligible inquiries received produce a validated, source-supported AI answer within 15 seconds at the selected workload | Collins supplies capacity/evidence-policy inputs; David defines measurement and verification |
| Overall deadline | 20 seconds | Hanlin contracts; Collins outcome mapping |
| Provider deadline | At most 12 seconds, reduced by remaining overall budget | Collins/Hanlin reconcile Hanlin's 15-second maximum; leave retrieval/validation time |
| Retrieval/customer lookup | Up to 2 seconds each; avoid unnecessary lookup | Hanlin's proposed bounds; review required |
| Successful durable support save | 95% within 2 seconds | David measurement definition; no false acknowledgements |
| Customer inquiry admission | One active inquiry/customer; retain proposed 5/minute maximum | Hanlin scope and retry semantics |
| Customer support submissions | Retain proposed 5/hour maximum | Hanlin + Collins review legitimate use |
| AI waiting queue | None initially; admit within budget or return busy | Vlad + Collins; differs from bounded-queue alternative |
| Prototype generation concurrency | Up to 5 only if selected model/account permits; also enforce RPM/token budgets | Collins actual account/model evidence; concurrency alone is not pacing |
| Production concurrency/replicas | Undetermined | Vlad + Collins + David: service times, quotas and resources |
| Automatic generation retries | Zero | Collins normalized failure policy |

Eligible inquiries are valid, authorized, in-scope questions supported by approved knowledge and assigned to AI by the agreed routing policy. Identify eligibility before admission; fix the supported question set before validation. Otherwise-eligible busy/rejected requests, provider failures, timeouts, invalid answers and unnecessary fallback remain in the denominator and miss the target. Appropriate clarification or human escalation for genuinely unsupported/complex questions is a separate outcome.

Measure from application receipt to the complete returned answer. Report offered, eligible, admitted, answered within target, answered late, fallback, rejected, failed and timed-out counts separately. The 95% target applies to all eligible inquiries received, replacing the earlier successful-answers-only latency percentage. A 200 fallback is not an AI answer.

Plan capacity for the full selected workload, not only the successful fraction. At one model call/inquiry this requires 10,000 model calls/minute plus adequate token capacity. Provider/model allowances, routing fractions and production resources remain to be justified. AI admission must preserve resources for support saves/status checks; human staffing, support-workload capacity and response-time expectations remain separate inputs.

**Status:** Initial service target proposed by Vlad on November 1; feasibility and team agreement pending. Recovery and any p99 objectives remain open.

### D12 — Five support states and ownership

**Raised by:** Collins's five-state model, Hanlin's transitions, David's concurrency/access concerns. **Owners:** Hanlin table, Collins flow, David race checks.

`queued` has no owner. Atomic self-claim moves to `assigned`; the owner moves to `in_review`, then `waiting_for_customer` or `resolved`. A permitted customer reply returns waiting work to `in_review`, retaining its owner. Resolution is terminal initially. Permit the owner to release any unfinished owned state to `queued`, clearing ownership with a reason. No direct takeover, auto-dispatch, supervisor/reopen workflow or broker initially.

Require ownership and expected-version checks; conflicts must not silently overwrite work. The durable database-backed human-agent work queue is distinct from the absence of an AI waiting queue.

**Evidence/status:** Proposed. Provide the transition/required-field table and concurrent claim, non-owner, stale-version and late-reply examples. Releasing `in_review` or `waiting_for_customer` extends Hanlin's current release rule and needs agreement.

### D13 — Provider choice and capacity

**Raised by:** [Issue #5](https://github.com/vlad8110/deskguide/issues/5), earlier Cohere/Groq recommendations and David's quota concern. **Owner:** Collins, with Vlad/David capacity review.

Keep Cohere as the first prototype candidate; compare Groq using the same B05/B12 questions before choosing one exact model. Verify account eligibility, RPM/token/monthly allowances, output compatibility, data-use policy and latency. Do not add automatic second-provider failover; B17 remains consolidated into B11.

Official evidence inspected October 31: [Cohere](https://docs.cohere.com/v2/docs/rate-limits) lists free limited evaluation access, including 1,000 calls/month and 20 chat requests/minute for listed models. Several listed production models allow 500/minute; other variants require contact. At one model call/inquiry, 10,000/minute demand is 20 times 500/minute. [Groq](https://console.groq.com/docs/rate-limits) documents request/token limits and organization scope; verify the actual account tier instead of treating a generic table as a free allowance.

**Evidence/status:** Final provider/model and production capacity awaiting evidence. Collins supplies a sourced comparison, actual tier/model limits, permitted data and a production quota/cost feasibility proposal. Any smaller model-call fraction needs justification. Custom quota/dedicated capacity remains an option to investigate. Separate mocked load from small live compatibility checks.

### D14 — Shared circuit breaker

**Raised by:** Collins's requested policy and Hanlin V18. Numbers are Vlad's defaults for review. **Owners:** Collins behavior, David race/recovery review, Vlad shared-state design.

Open after 3 consecutive qualifying provider timeouts/connection/service failures within 60 seconds; successful provider calls reset the sequence. Cool down 30 seconds, then permit one shared recovery trial using a new admitted inquiry. Success closes; failure reopens. Do not automatically resubmit failed inquiries.

Across instances, use a PostgreSQL record scoped to provider/model/credential configuration, atomic state/version changes and a 20-second trial lease. Do not hold a database lock during the external call. Ignore obsolete trial results, recover expired leases and allow already-admitted calls to finish. Failure to obtain shared breaker/admission state must not launch unlimited calls; return a controlled unavailable outcome and preserve the support path where storage permits.

Respect 429 guidance and quota reset; do not probe exhausted daily/monthly quota every 30 seconds. Credential/configuration failures need correction. Customer validation failures, unsupported questions and semantic rejection are not provider outages. The [circuit-breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) supports these state concepts, not our exact values.

**Evidence/status:** Proposed. Collins should specify normalized categories and when counters, state and leases are updated, including successful-call resets. David should review one shared recovery trial, expired leases, stale results, quota resets and database-write contention. Shared PostgreSQL coordination and the existing thresholds remain proposals.

### D15 — Payload and token bounds

**Raised by:** Hanlin's proposed limits; total token bounds added during Vlad's review. **Owners:** Hanlin schemas, Collins model compatibility, David boundary checks.

Trim/validate questions at 1–1,000 characters. Retrieve 5 passages by default, at most 8, each at most 1,500 characters. Propose at most 4,096 complete input tokens, including instructions/question/evidence, and 512 output tokens, subject to the exact model. Select highest-ranked permitted passages that fit; eight maximum-size passages need not fit. Reject oversized customer input rather than silently alter it. Do not present truncated/incomplete output as complete.

Support content: 1–1,000 characters; optional note: 0–2,000; customer reply: 1–2,000; feedback comment: 0–500. Retain Hanlin's agent page sizes of 25/default and 100/maximum. Bound source-reference structure and response size too. Character, token and byte/request-size limits are distinct.

**Evidence/status:** Proposed; reconcile schemas, tokenizer/model compatibility and edge cases. The 4,096/512 values are proposals, not provider specifications.

### D16 — Minimum customer context and a concrete use case

**Raised by:** Hanlin V22 and David's minimum-data questions. **Owners:** Vlad scope, Hanlin C7, Collins routing, David non-disclosure.

General knowledge questions need no customer lookup. An explicit account-status operation reads only `customer_id` and `account_status`, returning an authorized deterministic template without AI. Initially omit `display_name` and `tier`; do not automatically send database fields to the provider. Explain unavailable required context without guessing, and offer support. Account changes remain human work. A customer-data outage must not block confirmed request saving using trusted identity.

**Evidence/status:** Proposed narrowing of Hanlin's four-field allowlist. Provide an account-status example, denied lookup and unavailable lookup. This supplements the required AI knowledge-answering feature.

### D17 — Customer reply endpoint

**Raised by:** Hanlin C4c; durable retry handling added during review. **Owners:** Hanlin contracts, Collins flow, David conflicts/recovery.

Keep text-only replies for the customer's own request in `waiting_for_customer`, 1–2,000 characters. Apply D09's proposed server-issued, registered identity, scoped to customer, parent request and reply operation. Save the reply and complete its receipt in one transaction, then move to `in_review` retaining the agent. A completed same-payload retry returns the original reply without adding a message or changing state. Missing registrations and expired unused IDs are rejected.

For a new reply, check ownership, state and expected version atomically with saving. A reply racing resolution must not revive a resolved request. Apply parent-request retention; completed reply receipts remain for the retained record's lifetime. Customers return to the application for updates. Initially exclude attachments, live chat, email notifications and reopening.

**Evidence/status:** Proposed; supply saved/lost-acknowledgement/state-conflict examples.

### D18 — Authentication and sessions

**Raised by:** Hanlin's bearer-header draft and David's session/CSRF questions. **Owners:** Hanlin contracts, David security/lifetimes, Vlad identity provisioning.

For a same-origin browser application, use an established server-side session library, opaque session ID cookies and shared PostgreSQL state. Configure `Secure`, `HttpOnly`, `SameSite=Lax`, login rotation, expiry and logout invalidation. Require CSRF protection for state-changing requests, not SameSite alone. Recheck authorization for protected operations. This choice simplifies the browser flow; it does not imply bearer tokens are inherently insecure or must be JWTs.

[Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/) and [Flask-Session configuration](https://flask-session.readthedocs.io/en/latest/config.html) support reviewing these controls. Default Flask client-side sessions are not the proposed shared server-side store.

**Evidence/status:** Proposed change. David should recommend idle/absolute lifetimes, renewal, invalidation/cleanup rules and whether a separate all-sessions logout is needed. Hanlin supplies cookie/CSRF contract examples. I will decide logout scope after that input and clarify production identity provisioning. Expiry values, logout scope and provisioning remain open.

### D19 — Rationale and principal tradeoff

**Raised by:** Assignment requirements; David supplied Parnas/rationale input and Collins supplied integration reasoning. **Owner:** Vlad assembles; all four review.

Use the [500-word draft](design-rationale.md) to explain focused modules, typed boundaries, external AI isolation, durable support and governed learning. Analyze one principal tradeoff: a modular application simplifies small-team development/operations, while separate services offer finer independent scaling/releases at greater operational cost. Whole-application replication does not establish capacity.

**Evidence/status:** Draft ready for review; provider, evidence-policy and capacity clarifications pending.

### D20 — Planned quality and capacity validation

**Raised by:** David's staged plan; Vlad's review supplied the selected rate and precise proposed synchronized burst interval. **Owner:** David; Vlad resources, Collins quotas, Hanlin expected outcomes.

With mocked dependencies/synthetic data, start at 1–10 clients, then 100/1,000 sessions, then controlled ramps to 5,000/10,000. Propose 10 minutes at 166.67 inquiries/second, a 2× burst at 333.33/second for 2 minutes, and a separate bounded 10,000-arrivals-in-one-second overload case. Agree resource limits and stop conditions before execution. Simulate provider/DB failures and application restart.

Record offered/accepted/answered rates, p50/p95/p99 by outcome, fallbacks/errors, concurrency, resource/connection use, support-save integrity, rejection and recovery. Preserve B12's fixed 20 questions: 12 supported, 4 unsupported, 4 ambiguous; proposed gate 10/12 supported correct and all 4 unsupported fallback, with ambiguous cases reviewed individually. Ten sequential prototype timings are separate from load evidence.

**Evidence/status:** Planned; no executed results. Small live-provider smoke checks establish compatibility, not 10,000-user capacity.

### D21 — Review and final agreement

**Raised by:** Work plan, teammate open questions, Vlad's request for ownership/evidence. **Owner:** Vlad coordinates; all four review the final version.

David reviews architecture, Collins contracts, Hanlin AI flows, and Vlad verification. Vlad also plans to inspect PRs #16–#18. Reconcile M1–M9/C1–C10, fields, permissions, states, bounds, errors, retention and provider constraints. Distinguish Hanlin's V-prefixed validation values from David's V-prefixed test cases; their numbers refer to different things.

Consolidate responses into the shared architecture sources, contracts and rationale, then refresh repository snapshots. Each member reviews the same identified final version.

**Evidence/status:** Review planned; team approvals and final submission pending.

## 4. Responsibility and evidence queue

Reply in your existing issue or PR review with the D-number, clarification, supporting evidence and suggested wording.

| Person / existing issue | Clarify or provide | Evidence for current design | Review support |
| --- | --- | --- | --- |
| **Vlad — [#11](https://github.com/vlad8110/deskguide/issues/11)** | Keep the D11 service target and D09/D17 submission-ID approach proposed; resolve logout scope after security input; consolidate accepted decisions | Workload/deployment assumptions, production dependencies and one aligned final specification | David architecture; whole team final |
| **Collins — [#13](https://github.com/vlad8110/deskguide/issues/13)** | D03/D04/D11/D13/D14: exact provider/model/tier limits, expected model-call fraction, runtime evidence policy, failure outcomes and breaker behavior | Current quota/data-use sources; capacity proposal for the selected workload and 95% target; evidence/fallback examples; counter/state/lease and quota-reset rules | Hanlin AI flow; David reliability/privacy |
| **Hanlin — [#12](https://github.com/vlad8110/deskguide/issues/12)** | D05/D09/D12/D17/D18: review server-issued IDs, expiry/retry contracts, feedback expiry, session/CSRF behavior and agent conflicts; align C1–C10 | Issuance and transaction/uniqueness rules; same/changed/expired-ID examples; late/duplicate reply cases; session and feedback responses | Collins interfaces; David verification |
| **David — [#14](https://github.com/vlad8110/deskguide/issues/14)** | D09/D11/D12/D14/D17/D18/D20: recommend session/unused-ID lifetimes, logout/retention rules and verification of the new proposals | Concrete security/expiry recommendations; receipt/purge/backup/audit boundaries; eligible-inquiry denominator and test window; agent/breaker race cases | Vlad verification; whole team cross-component findings |

### Differences requiring explicit agreement

| Current draft/open question | Proposed resolution | Primary response |
| --- | --- | --- |
| Hanlin: bearer headers | Server-side cookie sessions plus CSRF (D18) | Hanlin + David |
| Collins: bounded AI queue | No initial AI waiting queue; bounded admission (D11) | Collins + Vlad |
| Hanlin: provider maximum 15 seconds | At most 12 seconds/remaining budget (D11) | Collins + Hanlin |
| Hanlin: proposed 24-hour submission retention | Request-lifetime duplicate protection; explicit expiry behavior (D09) | Hanlin + David + Collins |
| Hanlin: browser-generated submission UUID | Server-issued ID registered before use; unknown IDs cannot create requests (D09/D17) | Hanlin + David |
| Earlier latency percentage counts successful answers only | At least 95% of all eligible inquiries received yield supported AI answers within 15 seconds (D11) | Collins + David + Vlad |
| Hanlin: four customer fields | Two-field deterministic account-status path (D16) | Hanlin + Vlad |
| Hanlin: feedback requires answer ID | Inquiry identity sufficient without an answer (D05) | Hanlin + Collins |
| Hanlin: every internal call has access context | Protected operations get context; provider gets sanitized data (D06) | Hanlin + Collins |
| Hanlin: release only from assigned | Owner release from unfinished owned states with reason (D12) | Hanlin + David |
| David: illustrative 33.3/second baseline | Selected 166.67/second; retain lighter sensitivity case (D01) | David + Vlad |
| Semantic-support rule open | Define runtime policy and manual evaluation; no correctness guarantee (D03) | Collins + David |

## 5. Approval register and next revision

| Member | Review evidence/status | Final approval |
| --- | --- | --- |
| Vlad | First draft reviewed; reviews of PRs #16–#18 planned | Pending for combined final version |
| Hanlin | Draft PR #17; response to this log pending | Pending |
| Collins | Draft PR #16 and COMMENTED review on PR #17; response pending | Pending |
| David | [Review received](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5725784156); workload interpretation accepted; verification draft updated in PR #18; follow-up recommendations requested | Pending |

I will update the affected recommendations and rationale after the team replies. Follow the existing [delivery schedule](week-3-delivery-schedule.md) for combined review and corrections.

## 6. Revision record

| Revision | Date | Change | Review state |
| --- | --- | --- | --- |
| 1 | 2026-10-31 | D01–D21, source revisions, proposals, role-based evidence queue, approval register and rationale draft | Published for team review; technical/final approvals pending |
| 2 | 2026-10-31 | Editorial cleanup | Team review pending |
| 3 | 2026-11-01 | David's review recorded; service target, registered submission IDs and focused owner requests | Proposals pending responses and final agreement |
