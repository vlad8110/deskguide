# Unit 3 Design Decisions and Review Log

Coordinator: Vladimyr Merci, Lead Architect. Updated: November 3, 2026. Revision 13.

I have worked through the open architecture questions and collected my proposed solutions here. Please review the items assigned to your role, flag concerns, and provide the requested clarification or evidence. I will reconcile the replies before assembling the final specification.

**Status: Working proposals for team review.** Read the [complete revised proposed decisions](proposed-decisions.md). **Responses are due Tuesday, November 3, 2026, at 10:00 a.m. Eastern** in your existing issue or section PR so I can prepare the final revision. The [rationale draft](design-rationale.md) remains pending final alignment.

## 1. Sources and inspected revisions

| Source | Revision inspected | Evidence supplied |
| --- | --- | --- |
| [Vlad's architecture, PR #15](https://github.com/vlad8110/deskguide/pull/15) | `ff5c281f2db236a1f2846b5a53a340d709af2ec3`, November 1 baseline | Scope, selected workload, nine logical components, walkthroughs and shared sources |
| [Collins's integration flows, PR #16](https://github.com/vlad8110/deskguide/pull/16) | `0099cd842ff02463f6ad6adf5ff4e887fb501280` | Extractive evidence manifest, shared-breaker counting/recovery, revised routing and provider research; proposals, not test results |
| [Hanlin's contracts, PR #17](https://github.com/vlad8110/deskguide/pull/17) | Draft 3.2, `253be0deb5f3f96b75373de9925e4df8d4035d97` | Registered IDs/receipts, C1 selector, C1–C10, sessions, release permissions and denominator-aware measurements |
| [Collins's review of Hanlin's draft](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5725100910) | `95875135e8940f4ec44e7b431c1c9c0504fccf55`, October 31 | Specific authorization-context, semantic-support, feedback and timeout questions; COMMENTED review, not approval |
| [David's verification package, PR #18](https://github.com/vlad8110/deskguide/pull/18) | `9aa7a493dc5c4ff922d4ce2ace8744b3283a0a2b` | Revised verification package, N01–N15 and proposed B12 fixture manifest; execution and final approval pending |
| [David's review of the proposals](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5725784156) | Review of `13b635fc743ef4f3cc9b1318adcfa0bdcb3a1405`, October 31 | Workload interpretation accepted; capacity, expiry, session, ownership, grounding and breaker details remain open |
| [David's revised-architecture review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5730726420) | November 1, review of the revised architecture/diagrams | State-name mismatch, registered IDs, session/retention proposals, fixed eligibility labels and recovery checks |
| [David's Draft 3.1 review](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5738959296) | November 2, review of `0e7f855` | Conditional acceptance of 30-minute/eight-hour sessions and 30-minute unused IDs; save-metric, retention, evidence and breaker follow-up |
| [David's outbound-data and notice proposals, issue #8](https://github.com/vlad8110/deskguide/issues/8#issuecomment-6590423959) | November 2, 5:46:57 p.m. Eastern | Deny-by-default external generation, pre-submission notice and planned privacy checks; not implemented or tested |
| [David's provider comparison, issue #5](https://github.com/vlad8110/deskguide/issues/5#issuecomment-6590430685) | November 2, 5:47:19 p.m. Eastern | Official provider-policy research; actual tier/model, configured controls, capacity and provider choice remain open |
| [Assignment requirements](assignment-requirements.md) | Course instructions linked there | Diagram, typed contracts, 500-word rationale; 10,000 concurrent users without a specified inquiry frequency or latency target |

The [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit) and [shared draw.io diagram](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO) remain the editable architecture review sources. The local [complete architecture review document](architecture-first-draft/architecture-review.md) and written sections reflect the November 2 shared wording with the accepted-backup correction. The local [two-page diagram and PNGs](architecture-first-draft/README.md#diagrams) include the backup and connection corrections. Shared-source alignment and final team agreement remain pending.

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
| November 2 privacy follow-up | Vlad selected David's outbound-data rule and notice for inclusion as D22/D23 proposals. Exact policy, wording, provider controls and final team approval remain pending. |

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

**Evidence/status:** Collins's section 5 now proposes an exact-alias, versioned extractive manifest and exact approved-answer matching, with no extra model call and fail-closed checking. This is a narrow prototype policy: unlisted questions and paraphrased answers fall back. The manifest, aliases and source labels are not yet supplied or evaluated. C10's request-specific expected-answer input needs alignment; see the November 3 review below. No completed supported-answer functionality or passed service target is claimed. B12 manual evaluation remains separate.

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

**Raised by:** Collins's improvement flow and Hanlin's approver question. **Owners:** Collins walkthrough, Hanlin C6, Vlad release coordination and remaining independent review; David’s planned N09 checks are received.

A contributor proposes a bounded source/retrieval/prompt/configuration change. A different qualified member reviews it, evaluation passes and a rollback reference is recorded before release. Vlad is the primary release authorizer and Hanlin is the accepted backup. David declined the additional role; Hanlin confirmed availability in direct response to the backup-role request. The author cannot give final release authorization. A designated non-author must authorize a change; hold release if no qualified independent authorizer is available.

An independent qualified reviewer may also authorize release. Enforce a specific release permission and release exactly the reviewed/evaluated version. Vlad or the designated backup may restore a previously approved version with a recorded reason. Approved source changes enter M3/C8; approved generation configuration enters M4. Use the existing workflow; no automatic retraining or release from ratings.

**Evidence/status:** Proposed. David explicitly declined backup authorization in [PR #18](https://github.com/vlad8110/deskguide/pull/18#issuecomment-6590781449). Hanlin Draft 3.2 defines non-author permission and exact evaluated-version release; David N09 defines the planned checks. Hanlin accepted the backup role; the design and final combined-version approval remain pending. Vlad coordinates remaining independent review.

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

**Evidence/status:** Collins's section 10 now specifies qualifying categories, shared completion/epoch recording, rolling-window resets, one recovery lease, expired-lease recovery, stale-result exclusion and quota/configuration disable rules. Retain the proposed numeric settings for review. Clarify the availability denominator and stage-dependent response mapping below. Independent review and eventual recovery/contention tests remain pending; this specification does not establish capacity.

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

The shared Google Doc and draw.io now reflect the November 2 proposals, and the Design rationale tab contains the current draft. Local diagram/PNG and written snapshots have been reconciled with the November 2 shared sources and the pending backup/connection corrections; shared-file correction and publication remain pending. Reconcile owner responses and align the final document, diagram, contracts and rationale, then obtain all four explicit reviews of one identified final version.

**Evidence/status:** Vlad reviewed the proposed direction; David subsequently declined backup authorization. Hanlin accepted replacement backup responsibility. Final team approval, remaining owner evidence and submission remain pending.

### D22 — Outbound-data eligibility for external AI

**Raised by:** [David's issue #8 proposal](https://github.com/vlad8110/deskguide/issues/8#issuecomment-6590423959), supported by his [issue #5 provider comparison](https://github.com/vlad8110/deskguide/issues/5#issuecomment-6590430685). **Owners:** Vlad trust boundary and classification approval, Collins outbound policy/provider controls, Hanlin contract outcomes, David verification.

Deny externally hosted generation unless both the user question and every retrieved passage included in the request are explicitly eligible. Proposed eligible classes are synthetic, public or specifically approved for the selected external model. Internal-confidential material, personnel/HR complaints, credentials, regulated or restricted records and unclassified/unapproved content are blocked unless separate documented authorization and controls permit the specific disclosure. Minimize unnecessary identifiers; redaction alone does not establish eligibility. Enforce the decision server-side before the provider call. If eligibility or required provider controls cannot be established, make no external call and use an authorized retrieval-only response or human-support path; local/restricted inference requires a separately approved configuration.

Keep the classroom prototype limited to fictional questions and passages. Preserve D16's account-status path: fixed authorized response, no model generation and no customer-database fields sent to AI. D09's application retention rules do not establish provider retention; Collins must confirm the exact tier/model, actual data controls, exceptions, permitted data, quotas and cost under D13 before recommending the provider. Cohere remains the first prototype candidate for comparison with Groq; this proposal does not select either provider.

**Evidence/status:** Included at Vlad's direction as a proposal for team agreement, not implemented or tested. Approve the classification labels, decision authority and enforcement/fallback contract. David should verify allowed synthetic requests, restricted/unclassified questions and passages, absence of blocked outbound calls, and content-free diagnostics using synthetic fixtures.

### D23 — External-AI notice before question submission

**Raised by:** [David's proposed notice in issue #8](https://github.com/vlad8110/deskguide/issues/8#issuecomment-6590423959). **Owners:** Hanlin notice/confirmation UI, Collins provider-specific accuracy, Vlad design alignment, David verification.

Place a clear notice adjacent to the question box before submission. Proposed wording:

> DeskGuide may send your question and approved reference passages to an external AI service. Do not enter confidential personnel information or credentials. DeskGuide does not save ordinary questions and answers as conversation history. The external provider may retain data under its applicable terms and configured controls. If you choose human support, you will review and confirm the exact content before it is shared.

Reconcile the final wording with D09, D13, D16 and D22 and the selected provider's verified behavior. Distinguish DeskGuide's no-history rule from provider-held copies and from consented support records. A notice does not authorize restricted disclosure or replace outbound eligibility enforcement. The human-support preview must allow editing/cancellation and require confirmation before saving/sharing the support record.

**Evidence/status:** Draft wording selected for inclusion as a proposal; team approval and implementation remain pending. Hanlin aligns the UI/contract and Collins verifies the provider statement. David verifies visibility before submission, consistency with actual storage/outbound behavior, and preview/confirm/cancel outcomes. No completed tests are claimed.

## Current revision alignment

| Item | Current evidence | Remaining action |
| --- | --- | --- |
| Sessions and provisioning | Hanlin Draft 3.2 C9/C9c and David N01/N02 define the 30-minute/eight-hour rules, role-change revocation and controlled accounts | Final integrated review; execution is future work |
| Registered IDs | Draft 3.2 C4 and David N03–N06 define fixed expiry, combined three-ID cap, no eviction, receipt lifetime and retry races | Final integrated review and eventual tests |
| Explicit account status | Draft 3.2 C1 adds `requested_operation`; C7 and David N08 keep lookup read-only and outside AI | Collins aligns Flow A with the selector and zero model calls |
| Save and AI measurements | Draft 3.2 section 2.7/V31 and David section D include all eligible/confirmed outcomes and first-submit timing across retries | Approve final measurement contract with provider/resource limits |
| Release authority | Draft 3.2 C6/V35 and David N09 preserve non-author permission and exact evaluated versions; Hanlin accepted backup responsibility after David declined | Record Hanlin as backup in the final shared sources and C6; retain non-author authorization |
| Diagrams | Local M8 label, browser C2b/C9 labels and M2–M9/M4–M9 connections corrected | Reconcile the corrected source/PNG with shared files and final review version |
| B12 fixture manifest | David proposes 12 supported, four unsupported and four ambiguous cases | Lock actual synthetic sources, hashes/spans and independent labels. U01/U02/U04 are privacy/authorization cases; add ordinary missing-evidence coverage so the abstention check cannot pass through policy denials alone |
| Provider, evidence and breaker | Collins PR #16 at 0099cd8 supplies extractive evidence and shared-breaker proposals; reviewed below | Align the request-specific expected answer, availability counting and response mapping; supply the reviewed manifest and exact model/tier/quota/data controls |
| Cross-document wording | Draft 3.2 operative rules reflect many corrections | Reconcile the stale source-limit header and old change-history references; C1 `answer_id` wording must also cover deterministic account-status answers |

## 4. Responsibility and evidence queue

**Respond by Tuesday, November 3, 2026, at 10:00 a.m. Eastern** in your existing issue or section PR, using the D-number, clarification, evidence and suggested wording.

| Person / existing issue | Remaining input | Evidence/review |
| --- | --- | --- |
| **Vlad — [#11](https://github.com/vlad8110/deskguide/issues/11)** | Review production assumptions and cross-component findings; consolidate after the response cutoff; coordinate shared-source alignment | One consistent final document, diagram, contracts and rationale with all four reviews |
| **Hanlin — [#12](https://github.com/vlad8110/deskguide/issues/12), [PR #17](https://github.com/vlad8110/deskguide/pull/17)** | D07/D08/D09/D11/D12/D16/D17/D18: exact state, session/ID values, combined no-eviction ID cap, C1 selector, account/permission/release contracts, save timing and V28 | Concrete request/response and denied/conflict/expiry examples; align C1–C10 |
| **Collins — [#13](https://github.com/vlad8110/deskguide/issues/13), [PR #16](https://github.com/vlad8110/deskguide/pull/16)** | D03/D04/D11/D13/D14: clarify request-specific evidence expectation and availability counting; finalize the manifest, exact provider/model/quota/data policy and response alignment | Reviewed source/alias fixtures, supported/fallback examples, account-specific provider evidence and planned atomic window/lease checks |
| **David — [#14](https://github.com/vlad8110/deskguide/issues/14), [PR #18](https://github.com/vlad8110/deskguide/pull/18)** | Revised verification and N01–N15 posted; review coverage and proposed B12 manifest are available. David declined additional backup/urgent duties | Vlad coordinates remaining urgent review, independent fixture labels and final consistency; execution and final approval remain pending |

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
| Improvement release authority undefined | Vlad primary; Hanlin accepted backup; non-author authorization after independent review/evaluation | Hanlin + Collins + David |
| Prototype consecutive-failure breaker | Retain prototype rule; evaluate a separate production rolling-window candidate | Collins + David + Vlad |
| Evidence-policy proposal now received | Exact-alias/extractive prototype; explicit inquiry-bound expectation and reviewed manifest needed before activation | Collins + Hanlin + Vlad; independent fixture review |
| Outbound classification and enforcement not finalized | D22 deny-by-default rule for both questions and passages; fictional prototype data; approved fallback with zero blocked provider calls | Vlad + Collins + Hanlin + David |
| Pre-submission provider notice not finalized | D23 wording distinguishes application history, provider retention and confirmed human-support records | Hanlin + Collins + Vlad + David |

## 5. Approval register and next revision

| Member | Review evidence/status | Final approval |
| --- | --- | --- |
| Vlad | Reviewed the 14-topic November 2 proposed direction and revised rationale; shared sources aligned; owner evidence and final-version alignment pending | Pending for combined final version |
| Hanlin | Draft 3.2 at 253be0d in PR #17; requested selector, session/ID, measurement and release rules incorporated; final cross-check pending | Pending |
| Collins | PR #16 at 0099cd8; evidence and breaker proposals reviewed below; contract, manifest and provider evidence remain open | Pending |
| David | Revised six-file PR #18 at 9aa7a49, N01–N15 and proposed B12 manifest received; backup role declined; final fixture lock and integrated review pending | Pending |

After the response cutoff I will consolidate remaining findings and align the final specification. Follow the [delivery schedule](week-3-delivery-schedule.md). A response cutoff is not final technical approval.

### November 3 review — Collins's evidence and breaker proposals

Vlad selected the following direction on November 3: adopt the narrow extractive prototype with an explicit inquiry-bound evidence expectation; retain the breaker settings and shared-state recovery rules; clarify availability counting and stage-dependent responses. These coordinator decisions are recorded in the [revised decisions](proposed-decisions.md#7-ai-evidence-support-policy--d03c10). Final integrated team approval, manifest activation and implementation evidence remain pending.

| Item | Review finding and proposed solution | Owner / remaining evidence |
| --- | --- | --- |
| Evidence policy scope | Exact aliases and exact approved extractive answers provide a conservative prototype boundary. They reject otherwise useful paraphrases and unlisted questions. The approved answer exists before generation, so the model adds no free-form synthesis under this policy. Vlad accepts this limited feature for the prototype; broader semantic answering requires a separate reviewed policy. | Vlad and Collins confirm product scope; retain B12 independent source/answer review. |
| Inquiry-bound expected answer | Collins selects an approved answer before C3, but C10 currently exposes only candidate and retrieved/cited passages to its policy. Pass an immutable, request-scoped evidence expectation containing policy/manifest version, intent ID, approved answer and required source references/excerpt spans. Bind it before generation; never infer the expectation from the candidate or store it in shared mutable request state. Missing expectation fails closed. This internal context contains permitted knowledge only and adds no customer/session data to the provider request. | Hanlin aligns the C10 type/signature; Collins specifies coordinator handoff and canonical excerpt offsets. |
| Fixture and service-target accounting | Supply exact synthetic source versions, aliases, excerpts and independent eligibility labels before activation. Fix question eligibility before testing. An eligible question that misses alias matching or produces a rejected paraphrase remains a service-target miss. Include ordinary missing-evidence cases alongside privacy/authorization denials. | Collins supplies the manifest; Vlad coordinates independent fixture review using David's proposed B12 set. |
| Breaker structure and settings | Retain prototype three consecutive qualifying failures within 60 seconds; production candidate at least 50% failures after at least 20 completed calls in a rolling ten-second window. Retain 30-second cooldown, one globally leased recovery call and a 20-second lease. Collins's epoch, stale-completion, quota/configuration and unavailable-coordination rules address the principal recovery cases. Numeric settings remain provisional. | Collins owns the policy; independent recovery, race and database-contention checks remain planned. |
| Availability counting | A well-formed completed provider response contributes one availability success to the production denominator, even if C10 later rejects its content. Semantic rejection is not a qualifying provider failure; it must not remove an otherwise completed call from the denominator. The rejected answer remains a miss for the separate AI-service target. | Collins clarifies N/F wording; Hanlin aligns V18/C3 and planned examples. |
| Response mapping | Retain 503 SERVICE_BUSY with Retry-After when admission is denied before processing; an already-admitted inquiry receiving C3 circuit_open/provider failure returns controlled 200 temporarily_unavailable with a support option; hard overall-deadline expiry uses 504. Otherwise-eligible no-answer outcomes remain service-target misses. | Vlad proposes this stage distinction; Hanlin and Collins align the contracts/flows. |
| Remaining provider/capacity evidence | Cohere-first/Groq-comparison order remains. Exact account/model/tier controls, quotas, cost and measured latency are still required. Shared per-call database recording needs contention checks before any production-capacity claim. | Collins provides account-specific evidence; Vlad reviews resource assumptions. |

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
| 8 | 2026-11-02 | David's issue #8/#5 evidence recorded; D22 outbound-data rule and D23 pre-submission notice added at Vlad's direction | Policy, notice wording, provider evidence and final team approval pending; implementation/tests not completed |

| 9 | 2026-11-02 | David’s revised verification package, Hanlin Draft 3.2, pending replacement backup and diagram corrections | Local correction draft; owner evidence and all four final-version approvals pending |

| 10 | 2026-11-03 | Hanlin accepted backup authorization; Collins’s revised evidence and breaker proposals received for review | Role recorded locally; technical and final-version approvals pending |

| 11 | 2026-11-03 | Vlad selected the extractive prototype, inquiry-bound expectation, breaker settings, availability counting and response-stage rules | Coordinator direction recorded; final team approval, fixtures and executed validation pending |

| 12 | 2026-11-03 | Combined contracts Draft 3.3, revised integration flows and N16–N21 planned checks aligned locally with the selected direction | Candidate review pending; manifest, provider evidence and executed validation remain open |

The combined candidate contains Hanlin's 253be0d contracts, Collins's 0099cd8 flows and David's 9aa7a49 verification material with coordinator alignment. C10 now defines an immutable inquiry-bound expectation, exact-match policy and canonical excerpt offsets. C3/C1 distinguish provider availability from answer quality and admission denial from admitted failure. Hanlin is recorded as backup. See the [final review request](final-review-request.md) for the candidate identifier and remaining evidence. Earlier requests to define these interfaces are addressed by this candidate; owner review is still required.

| 13 | 2026-11-03 | Shared draw.io component/production pages and both PNGs aligned to Draft 3.3 contracts; November 3 C2 review candidate | All member approvals remain pending for the revised version; shared Google Doc text/image reconciliation remains separate |
