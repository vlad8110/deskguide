# Unit 3 Design Decisions and Review Log

Coordinator: Vladimyr Merci, Lead Architect. Updated: November 2, 2026. Revision 6.

I have worked through the open architecture questions and collected my proposed solutions here. Please review the items assigned to your role, flag concerns, and provide the requested clarification or evidence. I will reconcile the replies before assembling the final specification.

**Status: Working proposals for team review.** Read the [complete revised proposed decisions](proposed-decisions.md). **Responses are due Tuesday, November 3, 2026, at 10:00 a.m. Eastern** in your existing issue or section PR so I can prepare the final revision. The [rationale draft](design-rationale.md) remains pending final alignment.

## 1. Sources and inspected revisions

| Source | Revision inspected | Evidence supplied |
| --- | --- | --- |
| [Vlad's architecture, PR #15](https://github.com/vlad8110/deskguide/pull/15) | `ff5c281f2db236a1f2846b5a53a340d709af2ec3`, November 1 baseline | Scope, selected workload, nine logical components, walkthroughs and shared sources |
| [Collins's integration flows, PR #16](https://github.com/vlad8110/deskguide/pull/16) | `bcf86e01b779436325c4956773cd91cffa7e8276` | Answering, failure, escalation, improvement and bounded-queue proposals |
| [Hanlin's contracts, PR #17](https://github.com/vlad8110/deskguide/pull/17) | Draft 3.1, `0e7f85585c5887999d78337084185538822a9096` | Registered IDs/receipts, C1–C10, cookie sessions, evidence-policy interface and revised examples |
| [Collins's review of Hanlin's draft](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5725100910) | `95875135e8940f4ec44e7b431c1c9c0504fccf55`, October 31 | Specific authorization-context, semantic-support, feedback and timeout questions; COMMENTED review, not approval |
| [David's verification package, PR #18](https://github.com/vlad8110/deskguide/pull/18) | `a9912c913e477b591bb801e48a5387a81b46104b` | Updated selected-workload and burst scenarios, security/reliability checks, and response to D01–D21 |
| [David's review of the proposals](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5725784156) | Review of `13b635fc743ef4f3cc9b1318adcfa0bdcb3a1405`, October 31 | Workload interpretation accepted; capacity, expiry, session, ownership, grounding and breaker details remain open |
| [David's revised-architecture review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5730726420) | November 1, review of the revised architecture/diagrams | State-name mismatch, registered IDs, session/retention proposals, fixed eligibility labels and recovery checks |
| [David's Draft 3.1 review](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5738959296) | November 2, review of `0e7f855` | Conditional acceptance of 30-minute/eight-hour sessions and 30-minute unused IDs; save-metric, retention, evidence and breaker follow-up |
| [Assignment requirements](assignment-requirements.md) | Course instructions linked there | Diagram, typed contracts, 500-word rationale; 10,000 concurrent users without a specified inquiry frequency or latency target |

The [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit) and [shared draw.io diagram](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO) remain the editable architecture review sources. The [two-page diagram and PNGs](architecture-first-draft/README.md#diagrams) reflect the November 2 proposals. The [complete architecture review document](architecture-first-draft/architecture-review.md) and written sections retain the November 1 Google Doc wording. Written-source alignment and final team agreement remain pending.

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
| November 2 direction | Vlad reviewed the 14-topic proposed list, selected David as backup release authorizer and set the response cutoff. Technical evidence and all four final-version reviews remain pending. |

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

Retrieve only permitted relevant passages. Collins must define executable pre-generation evidence sufficiency and runtime answer-support rules, thresholds, allowed inputs, failure behavior and any additional model calls. Check source membership, version, permission, resolvability and actual claim support; valid IDs, matching quotations and model confidence alone do not prove support.

If validation fails, times out or cannot run, suppress the candidate and return a controlled fallback with a support option; clarification may also be offered. Customer confirmation is required before saving support. No automatic generation retry.

**Evidence/status:** Hanlin's C10 now supplies the interface and fail-closed outcome. Collins's executable rule remains pending evidence. Retain that limitation in the draft without claiming completed supported-answer functionality or a passed service target. David verifies supported, unsupported and check-unavailable cases; B12 manual evaluation remains separate.

### D04 — Failures and acknowledgements

**Raised by:** Collins's review/failure flows and David's durable-save checks. **Owners:** Collins outcomes, Hanlin contracts, David failure review.

Use 200 `temporarily_unavailable` for a delivered controlled provider-unavailable outcome and support offer; it is not an AI-answer success. Use 429 for customer limits, 503 `SERVICE_BUSY` for aggregate admission overload and 504 `DEADLINE_EXCEEDED` when the overall deadline expires and a response is still deliverable. Keep C10 validation failures distinct.

Use a 20-second overall deadline, at most 12 seconds for the provider and a one-second fallback reserve. Shorten dependency waits by the remaining budget; stop waiting by approximately second 19. Return fallback as soon as failure is known. Ignore late results and do not automatically resubmit failed inquiries or save support requests.

Known failed save means “not saved”; unknown commit means “confirmation unavailable,” followed by same-ID lookup/retry. Acknowledgement requires durable persistence. Preserve unsent text in the current view without promising reload persistence.

**Evidence/status:** Proposed, including Hanlin's one-second reserve accepted by Vlad for team review. Collins confirms the outcome/timing table; Hanlin aligns contracts; David verifies timeouts, disconnects, lost acknowledgements and late results.

### D05 — Feedback without an answer

**Raised by:** Collins's PR #17 question 3: C6 requires `answer_id`, but some inquiries never create one. **Owners:** Hanlin C6, Collins flow, David access/expiry.

Require `inquiry_id`, rating and optional comment; verify inquiry ownership. Derive outcome/configuration from trusted metadata. Do not require an answer ID; retain a nullable internal link where an answer exists. Keep Hanlin's optional category if valid for the outcome. Pre-inquiry rejection creates no separate feedback feature.

**Evidence/status:** Draft 3.1 addresses feedback without an answer and expiry with inquiry metadata. Team agreement and David's deletion/access checks remain pending.

### D06 — Authorization context

**Raised by:** Collins's PR #17 question 1: C9's blanket first-argument rule conflicts with C3 `generate(request)`. **Owners:** Hanlin signatures, Collins outbound payload, David boundary review.

Protected application operations receive verified `AccessContext`. Keep `generate(request)` limited to sanitized generation data and a safe correlation ID; never serialize credentials, session tokens, roles or the internal authorization object to the provider. Revise “every internal method” instead of adding unused authority parameters to pure helpers.

**Evidence/status:** Draft 3.1 supplies the C3 exception, permitted payload and forged-context example. Final cross-contract alignment and verification remain pending.

### D07 — Company/customer isolation

**Raised by:** Hanlin V20 and David's isolation questions. **Owners:** Vlad scope, Hanlin role matrix, David denial checks.

Use one company initially without multi-company tenancy. Provision fictional prototype accounts through a protected management command or approved bulk import, with no public self-registration or role-selection screen. Map customer accounts to approved customer IDs from the existing customer database while retaining password hashes and roles in a separate controlled application account store. C7 remains read-only.

Customers see their own records; agents see the unassigned work queue and their own assigned requests. Administrators manage knowledge documents without automatic support-content or feedback access. Assign reviewer and release permissions explicitly. Scope is server-derived and checked for every protected object operation. Account/permission changes revoke existing sessions.

**Evidence/status:** Vlad's proposed single-company/provisioning direction. Hanlin supplies the role/operation matrix and provisioning contracts; David verifies denied/cross-customer access and role-change revocation. Multi-company support remains deferred.

### D08 — Improvement and release authority

**Raised by:** Collins's improvement flow and Hanlin's approver question. **Owners:** Collins walkthrough, Hanlin C6, David review, Vlad release coordination.

A contributor proposes a bounded source/retrieval/prompt/configuration change. A different qualified member reviews it, evaluation passes and a rollback reference is recorded before release. Vlad is the primary release authorizer; David is the backup. The author cannot give final release authorization. When Vlad authors, David authorizes; when David authors, Vlad authorizes. If neither is independent and available, designate another qualified non-author before release.

An independent qualified reviewer may also authorize release. Enforce a specific release permission and release exactly the reviewed/evaluated version. Vlad or David may restore a previously approved version with a recorded reason. Approved source changes enter M3/C8; approved generation configuration enters M4. Use the existing workflow; no automatic retraining or release from ratings.

**Evidence/status:** Proposed. Independent review existed earlier; non-author release authorization and David's backup designation are November 2 refinements selected by Vlad. Hanlin aligns C6 permissions; Collins supplies the flow; David verifies self-authorization denial and rollback.

### D09 — Retention and duplicate-protection lifetime

**Raised by:** Hanlin V11/V21 and David's privacy review. Durations are Vlad's proposed defaults. **Owners:** David retention/security, Hanlin expiry contracts, Collins feedback utility.

Keep these proposed durations:

| Data | Retention |
| --- | --- |
| General chat transcripts | Do not persist |
| Minimal inquiry metadata and linked feedback | 30 days from inquiry creation |
| Sanitized diagnostic logs | Seven days; no raw content, credentials or direct customer identifiers |
| Confirmed support content/replies and completed receipts | While open plus 30 days after resolution |
| Minimal support-action audit records | Follow the associated support request |
| Evaluation/release summaries | For active/retained rollback versions, then 30 days after associated version retirement |
| Encrypted daily backups | Seven-day rotation |

Block access at expiry, then purge live records in the next daily cleanup within 24 hours. Delete linked feedback with its inquiry metadata. Review old open work rather than automatically delete unresolved requests. Keep raw conversations/feedback out of audit/evaluation summaries. Track live purge separately from backup expiry; reapply current expiry rules and recorded deletions before restored data becomes available. Collins documents provider-held copies separately.

Server-issued submission/reply IDs are registered in PostgreSQL, bound to customer/operation and parent request where applicable. Only registered, unused, unexpired IDs may create records. Proposed validity is 30 minutes from registration, with three unused, unexpired IDs per customer combined across operations. A fourth registration returns 429 with a clear pending-limit message; never evict an older ID. Enforce the cap atomically and exclude expired registrations from its count.

| Submission identity | Behavior |
| --- | --- |
| Registered, unused and unexpired | Atomically save the request/reply and receipt, then acknowledge |
| Completed, same payload | Replay the existing authorized result; create nothing new |
| Completed, changed payload | Return a conflict |
| Expired unused ID | Reject; preserve text and require deliberate new registration/confirmation |
| Missing or purged registration/receipt | Reject; never recreate an old request from its ID |

Completed receipts remain with the retained request; unused-ID expiry never deletes them. Uncertain commits use the original ID for reconciliation, never an automatically generated replacement. Store a result reference and scoped payload-comparison value rather than another raw support-text copy; David reviews fingerprint/privacy details.

**Evidence/status:** Proposed. David conditionally accepts Hanlin's 30-minute/three-ID values. Draft 3.1 already rejects a fourth ID; combined-operation scope and no eviction need explicit wording. The earlier 24-hour V11 proposal concerned receipt retention, not unused-ID expiry. Hanlin aligns V11/V21/V25/V32/V33; David verifies purge, access, backup/restore and concurrent registration/commit/replay cases. Provider policy and actual deletion evidence remain pending.

### D10 — Deployment and storage

**Raised by:** David §4.2/XR02, asking how production differs from the local Flask/SQLite prototype. **Owner:** Vlad; David reviews bottlenecks.

Propose one modular Flask codebase, replicated behind HTTPS ingress/load balancing and a production WSGI server. Shared PostgreSQL holds durable DeskGuide records, server-side sessions and initial knowledge/version storage through component-owned adapters. M7 isolates the existing customer database. Keep SQLite locally. Initially avoid separate microservices, Kubernetes, Redis, a vector database and a broker.

This reduces separately deployed parts for junior developers while preserving interfaces. Replicas scale the whole application, not each logical module independently. Provider quotas, database connections and agent capacity remain constraints. [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/), [SQLite usage guidance](https://www.sqlite.org/whentouse.html) and [PostgreSQL concurrency documentation](https://www.postgresql.org/docs/current/mvcc.html) support evaluating these choices, not a capacity guarantee.

**Evidence/status:** Proposed. Vlad supplies deployment/state ownership and sizing reasoning. Hosting vendor, database version/size, replica count, availability topology and cost remain unselected.

### D11 — Performance and admission

**Raised by:** David's plan, Hanlin V4–V9/V14–V18 and Collins's queue proposal. Values are provisional, not measured.

| Setting | Proposal | Evidence/clarification owner |
| --- | --- | --- |
| Timely AI service | At least 95% of all eligible inquiries received produce a supported answer within 15 seconds at the selected workload | Collins evidence/provider inputs; David classification and measurement |
| Overall deadline / fallback reserve | 20 seconds / one second | Hanlin contracts; Collins outcomes |
| Provider wait | At most 12 seconds, shortened by remaining budget and reserve | Collins + Hanlin |
| Retrieval/customer lookup | Up to two seconds each; avoid unnecessary lookup | Hanlin's proposed bounds; review required |
| Confirmed support save | At least 95% of valid, confirmed intended submissions durably saved with success acknowledgement ready within two seconds of application receipt | Hanlin boundary; David outcome accounting |
| Customer inquiry admission | One active inquiry/customer; retain proposed 5/minute maximum | Hanlin scope and retry semantics |
| Customer support submissions | Retain proposed 5/hour maximum | Hanlin + Collins review legitimate use |
| AI waiting queue | None; bounded admission with immediate busy outcome | Vlad + Collins |
| Prototype generation concurrency | Up to five only if account/model permits; also enforce request/token budgets | Collins quota evidence |
| Planned peak factor | Two for the two-minute 333.33/second scenario | Vlad + David |
| Production concurrency/replicas | Pending measured service times, quotas and resource evidence | Vlad + Collins + David |
| Automatic generation retries | Zero; no automatic second-provider failover | Collins normalized outcomes |

Fix eligibility and routing before admission using an independently reviewed, pre-labeled supported-question set. Otherwise-eligible busy/rejected inquiries, provider failures, timeouts, invalid answers and unnecessary fallback remain in the denominator and miss the target. Report genuine unsupported/ambiguous outcomes, account status and explicit human requests separately. A 200 fallback is not an AI answer.

Measure AI service from application receipt to complete returned answer. Report received/eligible/admitted/timely/late/fallback/rejected/failed/timeout counts per scenario.

For support, start at receipt of the final confirmed submission; end at confirmed durable commit and success-response readiness. Exclude form editing, ID registration and human response time; measure registration separately. Slow saves, known failures, uncertain commits and capacity rejections count as misses. Count each intended submission once using its original ID/start time, while recording every retry attempt separately. Invalid, unauthorized, expired-ID and conflicting-payload attempts are reported separately. Later reconciliation cannot retroactively make a late save timely.

Plan for the full selected workload and include all external calls. AI admission and support admission are separately bounded. Twenty seconds minus a one-second reserve and a 12-second provider cap leaves seven seconds under the hard deadline; it does not establish the 15-second target. If the provider uses 12 seconds, only three seconds remain for other work to meet that target.

**Evidence/status:** November 2 proposals awaiting team agreement and validation. Provider/resources, production concurrency and recovery/p99 objectives remain open. Simulated application load is not external-provider capacity.

### D12 — Five support states and ownership

**Raised by:** Collins's five-state model, Hanlin's transitions, David's concurrency/access concerns. **Owners:** Hanlin table, Collins flow, David race checks.

`queued` has no owner. Atomic self-claim moves to `assigned`; the owner moves to `in_review`, then `waiting_for_customer` or `resolved`. A permitted customer reply returns waiting work to `in_review`, retaining its owner. Resolution is terminal initially. Permit the owner to release any unfinished owned state to `queued`, clearing ownership with a reason. No direct takeover, auto-dispatch, supervisor/reopen workflow or broker initially.

Require ownership and expected-version checks; conflicts must not silently overwrite work. The durable database-backed human-agent work queue is distinct from the absence of an AI waiting queue.

**Evidence/status:** Proposed. Draft 3.1 supplies the transition table and broader owner-release rule. Reconcile all state spellings to `waiting_for_customer`; David verifies concurrent claims, non-owner updates, stale versions, release and late replies.

### D13 — Provider choice and capacity

**Raised by:** [Issue #5](https://github.com/vlad8110/deskguide/issues/5), earlier Cohere/Groq recommendations and David's quota concern. **Owner:** Collins, with Vlad/David capacity review.

Keep Cohere as the first prototype candidate and compare Groq using the same B05/B12 questions before choosing an exact model. Verify actual account eligibility, request/token/monthly/concurrent-call allowances, output compatibility, data-use/retention policy and latency.

Free evaluation access is prototype-only. [Cohere's documented limits](https://docs.cohere.com/v2/docs/rate-limits) list 20 trial chat requests/minute and 1,000 calls/month; several production models list 500/minute while others require contact. The planning case of 10,000 model calls/minute is 20 times 500/minute. A paid key alone does not establish sufficient capacity. [Groq limits](https://console.groq.com/docs/rate-limits) must be checked against the actual model/account.

Collins supplies a sourced comparison, exact tier/model limits, permitted data, expected calls per inquiry and a production quota/cost feasibility proposal. Include any evidence-checking call. Any lower generation-call fraction requires justification. Keep prototype traffic fictional; separate simulated application load and small live compatibility checks. Automatic second-provider failover remains deferred.

**Evidence/status:** Exact model/account and production capacity pending evidence and team agreement. No service purchase is selected by these proposals.

### D14 — Shared circuit breaker

**Raised by:** Collins's requested policy and Hanlin V18. Numbers are Vlad's defaults for review. **Owners:** Collins behavior, David race/recovery review, Vlad shared-state design.

**Prototype:** open after three consecutive qualifying provider timeouts/connection/service failures within 60 seconds. A successful provider call resets this sequence.

**Production candidate:** open when at least 50% of completed provider calls in a rolling ten-second window are qualifying failures, after at least 20 calls have completed. This is a new provisional refinement for Collins and David to evaluate, not an established production setting. Ordinary successes contribute to the window rather than resetting it. Collins defines recording, reset and recovery-window semantics.

Both proposals retain a 30-second cooldown and one global recovery trial on a new admitted inquiry, protected by a 20-second lease. Success closes and failure reopens. Use a PostgreSQL record scoped to provider/model/credential configuration with atomic version changes. No database lock is held during the provider call. Ignore obsolete trial results, recover expired leases and allow already-admitted calls to finish. Shared-state failure returns a controlled unavailable outcome rather than launching unbounded calls. No automatic replay of failed inquiries.

Respect 429/quota-reset guidance; do not probe exhausted daily/monthly quota every 30 seconds. Credential/configuration failures require correction. Customer validation, unsupported questions and semantic rejection are not provider outages. [Sliding-window/minimum-volume guidance](https://resilience4j.readme.io/docs/circuitbreaker) supports the pattern, not the exact candidate values.

**Evidence/status:** Proposed. Collins specifies qualifying categories, counter/window/reset/write policy and lease events. David verifies one global trial, expired leases, stale results, quota reset, simultaneous completions and database contention. Vlad reviews the shared-state/resource assumptions.

### D15 — Payload and token bounds

**Raised by:** Hanlin's proposed limits; total token bounds added during Vlad's review. **Owners:** Hanlin schemas, Collins model compatibility, David boundary checks.

Trim/validate questions at 1–1,000 characters. Retrieve 5 passages by default, at most 8, each at most 1,500 characters. Propose at most 4,096 complete input tokens, including instructions/question/evidence, and 512 output tokens, subject to the exact model. Select highest-ranked permitted passages that fit; eight maximum-size passages need not fit. Reject oversized customer input rather than silently alter it. Do not present truncated/incomplete output as complete.

Support content: 1–1,000 characters; optional note: 0–2,000; customer reply: 1–2,000; feedback comment: 0–500. Retain Hanlin's agent page sizes of 25/default and 100/maximum. Bound source-reference structure and response size too. Character, token and byte/request-size limits are distinct.

**Evidence/status:** Proposed; reconcile schemas, tokenizer/model compatibility and edge cases. The 4,096/512 values are proposals, not provider specifications.

### D16 — Minimum customer context and a concrete use case

**Raised by:** Hanlin V22 and David's minimum-data questions. **Owners:** Vlad scope, Hanlin C7, Collins routing, David non-disclosure.

General knowledge questions need no customer lookup. Keep read-only account status through C1, selected explicitly by the customer. Add a requested-operation selector to C1; the response `route` alone is not a request selector. The server validates the requested operation and derives customer scope from the authenticated account.

Read only `customer_id` and `account_status` and return a fixed authorized template without retrieval/model generation. Omit display name/tier and never send customer-database fields to AI. Explain unavailable required data without guessing and offer support. Account changes go to a human. A customer-data outage must not block confirmed support saving with trusted identity.

**Evidence/status:** Proposed. Draft 3.1 adopts the two-field/read-only/no-generation path; the explicit request selector remains to be specified by Hanlin. Collins aligns routing; David verifies own/foreign/unavailable lookups and zero provider calls.

### D17 — Customer reply endpoint

**Raised by:** Hanlin C4c; durable retry handling added during review. **Owners:** Hanlin contracts, Collins flow, David conflicts/recovery.

Keep text-only replies for the customer's own request in `waiting_for_customer`, 1–2,000 characters. Apply D09's proposed server-issued, registered identity, scoped to customer, parent request and reply operation. Save the reply and complete its receipt in one transaction, then move to `in_review` retaining the agent. A completed same-payload retry returns the original reply without adding a message or changing state. Missing registrations and expired unused IDs are rejected.

For a new reply, check ownership, state and expected version atomically with saving. A reply racing resolution must not revive a resolved request. Apply parent-request retention; completed reply receipts remain for the retained record's lifetime. Customers return to the application for updates. Initially exclude attachments, live chat, email notifications and reopening.

**Evidence/status:** Proposed. Draft 3.1 supplies registered reply IDs and state/version examples; align the aggregate three-ID limit and 30-minute expiry, then verify duplicate/lost-acknowledgement/late-reply cases.

### D18 — Authentication and sessions

**Raised by:** Hanlin's bearer-header draft and David's session/CSRF questions. **Owners:** Hanlin contracts, David security/lifetimes, Vlad identity provisioning.

Use a maintained server-side session library, opaque session-ID cookies and shared PostgreSQL state. Retain Secure, HttpOnly, SameSite=Lax cookies and CSRF protection for state-changing requests. Recheck authorization and object scope on protected operations.

Propose a 30-minute idle limit and eight-hour absolute maximum. Authenticated activity renews idle expiry but never silently moves the absolute deadline within an existing session. Rotate IDs at login; account-role/permission changes revoke existing sessions and require another login. Current-session logout is the initial user-facing option. Enforce expiry/revocation across replicas independently of later cleanup.

Provision accounts through a protected management command or approved bulk import; no public self-registration or role picker. Seed fictional prototype accounts and map approved customer IDs from the existing customer database. Password hashes/roles belong in the controlled application account store; C7 remains read-only. Use one company initially and explicit reviewer/release permissions under D07/D08.

[Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/) and [Flask-Session configuration](https://flask-session.readthedocs.io/en/latest/config.html) support reviewing these controls. Default client-side Flask sessions are not the proposed shared store.

**Evidence/status:** Hanlin proposed 30 minutes/eight hours; David conditionally accepts them as stricter working defaults than his earlier 12-hour maximum. Vlad keeps them proposed with controlled provisioning and current-session logout. Hanlin supplies the concrete contracts; David verifies expiry, renewal, role changes, logout and denied access across replicas.

### D19 — Rationale and principal tradeoff

**Raised by:** Assignment requirements; David supplied Parnas/rationale input and Collins supplied integration reasoning. **Owner:** Vlad assembles; all four review.

Use the [500-word draft](design-rationale.md) to explain focused modules, typed boundaries, external AI isolation, durable support and governed learning. Analyze one principal tradeoff: a modular application simplifies small-team development/operations, while separate services offer finer independent scaling/releases at greater operational cost. Whole-application replication does not establish capacity.

**Evidence/status:** Draft ready for review; provider, evidence-policy and capacity clarifications pending.

### D20 — Planned quality and capacity validation

**Raised by:** David's staged plan; Vlad's review supplied the selected rate and precise proposed synchronized burst interval. **Owner:** David; Vlad resources, Collins quotas, Hanlin expected outcomes.

Use an independently reviewed, pre-labeled fixed supported-question set and routing policy before each run. Record expected outcomes and source versions. Preserve B12's 20 questions (12 supported, four unsupported, four ambiguous) and its existing proposed quality gates: 10/12 supported correct, all four unsupported fallback, ambiguous cases individually reviewed. Keep these checks separate from the production service targets.

With controlled dependencies and synthetic data, begin at 1–10 clients, then 100/1,000 sessions, then bounded ramps to 5,000/10,000. Proposed scenarios: ten minutes at 166.67 inquiries/second; a 2× 333.33/second peak for two minutes; and a separate 10,000-arrivals-in-one-second overload case. Agree resources and stop conditions before execution. Simulate provider/database failures and restart.

Record received/eligible/admitted/answered/late/fallback/rejected/failed/timeout counts, p50/p95/p99 by outcome, concurrency, resources/connections and support-save integrity. Eligible failures stay in the denominator. Report non-AI account status and explicit human requests separately. Verify session/ID expiry, cleanup/commit races, owner/version conflicts, non-author release permission, deletion/restore and shared-breaker recovery.

**Evidence/status:** Planned, not executed. David owns test-set versions and scenarios; Hanlin supplies expected contract outcomes; Collins supplies provider/policy limits; Vlad reviews resource assumptions. Small live checks establish compatibility, not 10,000-user capacity.

### D21 — Review and final agreement

**Raised by:** Work plan, teammate open questions, Vlad's request for ownership/evidence. **Owner:** Vlad coordinates; all four review the final version.

Responses to the [complete revised proposal](proposed-decisions.md) are due **Tuesday, November 3, 2026, at 10:00 a.m. Eastern** in existing issues or section PRs. Include D-number, remaining concern, suggested wording and supporting evidence. I will consolidate the replies into a final review version after the cutoff. Unanswered technical items remain open.

David reviews architecture, Collins contracts, Hanlin AI flows and Vlad verification. Reconcile M1–M9/C1–C10, account/status selectors, permissions, exact state names, bounds, errors, retention, release governance and provider constraints. Hanlin's V-prefixed proposed values and David's V-prefixed test cases are different numbering systems.

The shared Google Doc and draw.io now reflect the November 2 proposals, and the Design rationale tab contains the current draft. Repository diagram/PNG copies are current; repository written architecture snapshots remain dated November 1. Reconcile owner responses and align the final document, diagram, contracts and rationale, then obtain all four explicit reviews of one identified final version.

**Evidence/status:** Vlad reviewed the proposed direction and selected David as backup release authorizer. Final team approval, remaining owner evidence and submission remain pending.

## 4. Responsibility and evidence queue

**Respond by Tuesday, November 3, 2026, at 10:00 a.m. Eastern** in your existing issue or section PR, using the D-number, clarification, evidence and suggested wording.

| Person / existing issue | Remaining input | Evidence/review |
| --- | --- | --- |
| **Vlad — [#11](https://github.com/vlad8110/deskguide/issues/11)** | Review production assumptions and cross-component findings; consolidate after the response cutoff; coordinate shared-source alignment | One consistent final document, diagram, contracts and rationale with all four reviews |
| **Hanlin — [#12](https://github.com/vlad8110/deskguide/issues/12), [PR #17](https://github.com/vlad8110/deskguide/pull/17)** | D07/D08/D09/D11/D12/D16/D17/D18: exact state, session/ID values, combined no-eviction ID cap, C1 selector, account/permission/release contracts, save timing and V28 | Concrete request/response and denied/conflict/expiry examples; align C1–C10 |
| **Collins — [#13](https://github.com/vlad8110/deskguide/issues/13), [PR #16](https://github.com/vlad8110/deskguide/pull/16)** | D03/D04/D11/D13/D14: executable evidence rules, exact provider/model/quota/data policy, prototype vs production breaker and timing outcomes | Sourced capacity/cost/data-retention comparison, support/failure examples and atomic counter/window/lease events |
| **David — [#14](https://github.com/vlad8110/deskguide/issues/14), [PR #18](https://github.com/vlad8110/deskguide/pull/18)** | Review the proposed values and retention rules; define fixed eligibility labels, all-submission save accounting, release independence and race/recovery/restore cases | Identified test-set and scenario versions; distinguish planned checks, simulated results and live evidence; backup release authorizer |

### Differences requiring explicit agreement

| Earlier draft / current open issue | Current proposal | Primary response |
| --- | --- | --- |
| Earlier bearer-header authentication | Shared server-side cookie sessions, CSRF, 30-minute idle/eight-hour maximum, current-session logout | Hanlin + David |
| Collins's bounded AI queue | No initial AI waiting queue; aggregate bounded admission | Collins + Vlad |
| Earlier provider maximum 15 seconds | At most 12 seconds within remaining budget, with one-second fallback reserve | Collins + Hanlin |
| Earlier 24-hour receipt retention | Receipts follow the retained request; separate fixed 30-minute unused-ID expiry | Hanlin + David |
| Earlier browser-generated IDs | Server-issued registered IDs; max three unused/unexpired per customer across operations; fourth denied, no eviction | Hanlin + David |
| Successful-answer-only latency percentage | 95% of all eligible AI inquiries received answered within 15 seconds; eligibility fixed before testing | Collins + David + Vlad |
| Successful-save-only latency percentage | 95% of valid confirmed intended submissions durably saved/acknowledgement ready within two seconds; all outcomes reported | Hanlin + David |
| Earlier four-field customer context | Two-field read-only account status through explicit C1 requested operation; no AI | Hanlin + Collins + Vlad |
| Earlier feedback requires answer ID | Authorized inquiry identity sufficient without an answer | Hanlin + Collins |
| Earlier every internal method takes access context | Protected operations get context; provider receives only permitted generation data | Hanlin + Collins |
| Earlier release only from assigned support state | Owner release from unfinished owned states with reason; customer reply retains owner | Hanlin + David |
| Improvement release authority undefined | Vlad primary, David backup; non-author authorization after independent review/evaluation | Hanlin + Collins + David |
| Prototype consecutive-failure breaker | Retain prototype rule; evaluate a separate production rolling-window candidate | Collins + David + Vlad |
| Evidence-support policy still missing | Executable Collins policy; fail closed while evidence/thresholds remain pending | Collins + David |

## 5. Approval register and next revision

| Member | Review evidence/status | Final approval |
| --- | --- | --- |
| Vlad | Reviewed the 14-topic November 2 proposed direction and revised rationale; shared sources aligned; owner evidence and final-version alignment pending | Pending for combined final version |
| Hanlin | Draft 3.1 in PR #17; requested confirmations reflected in the revised proposal | Pending |
| Collins | Draft PR #16 and COMMENTED review on PR #17; assigned evidence/policy response pending | Pending |
| David | November 1 architecture review and November 2 Draft 3.1 review; conditionally accepts session/unused-ID values; asks for remaining policy/verification detail | Pending |

After the response cutoff I will consolidate remaining findings and align the final specification. Follow the [delivery schedule](week-3-delivery-schedule.md). A response cutoff is not final technical approval.

## 6. Revision record

| Revision | Date | Change | Review state |
| --- | --- | --- | --- |
| 1 | 2026-10-31 | D01–D21, source revisions, proposals, role-based evidence queue, approval register and rationale draft | Published for team review; technical/final approvals pending |
| 2 | 2026-10-31 | Editorial cleanup | Team review pending |
| 3 | 2026-11-01 | David's review recorded; service target, registered submission IDs and focused owner requests | Proposals pending responses and final agreement |
| 4 | 2026-11-01 | Shared architecture and component/deployment diagram copies aligned with the then-current proposals | Owner evidence and final team approval pending |
| 5 | 2026-11-02 | Draft 3.1 and David's latest reviews; revised 14-topic proposals, David as backup authorizer, refined measurements/retention/breaker and November 3 response cutoff | Team evidence, shared-source alignment and final-version approvals pending |
| 6 | 2026-11-02 | Shared component/deployment diagrams revised for current proposals; editable source and PNG previews refreshed | Written-source alignment, owner evidence and final-version approvals pending |
| 7 | 2026-11-02 | Rationale revision 3 and shared Google Doc rationale tab; updated shared-source alignment status | Owner responses and all four final-version approvals pending |
