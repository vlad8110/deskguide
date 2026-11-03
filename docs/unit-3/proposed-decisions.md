# DeskGuide — Revised Proposed Decisions

Vladimyr Merci | November 3, 2026

**Team response cutoff: Tuesday, November 3, 2026, at 10:00 a.m. Eastern.** Please provide your remaining feedback, corrections and supporting evidence in your assigned issue or section PR by then so I can prepare the final revision.

These are my proposed decisions for team review. Final team agreement and the evidence identified below remain pending. The [D01–D21 review log](design-decisions-and-review-log.md) records the original concerns, sources and owners.

## 1. State name — D12/D17

Use `waiting_for_customer` consistently in contracts, walkthroughs, examples and any diagram annotations containing the state name. A permitted customer reply returns the request to `in_review`, retaining the assigned agent. `resolved` remains terminal.

Hanlin aligns the wording; David verifies transitions and conflicts.

## 2. Session duration and security — D18

Keep a **30-minute inactivity limit** and an **eight-hour absolute maximum**. Authenticated activity renews the inactivity timer; the absolute deadline never slides within an existing session.

Rotate the session ID at login. Role or permission changes revoke existing sessions and require another login. Enforce expiry and revocation across application instances using shared server-side state. Current-session logout remains the initial user-facing logout option. Retain Secure, HttpOnly and SameSite=Lax cookies and CSRF protection for state-changing requests.

These are Hanlin's proposed values, subsequently accepted by David as working defaults. Hanlin defines the contract; David verifies renewal, expiry, role-change and logout cases.

## 3. Unused submission IDs — D09/D17

IDs expire **30 minutes after server registration**. Limit each customer to **three unused, unexpired IDs combined across escalation and reply operations**.

Reject a fourth registration with HTTP `429` and a clear "too many pending submissions" message. Never cancel an older ID to make room. Enforce the limit atomically; expired registrations do not consume an unused-ID slot even if cleanup has not run yet.

Bind each ID to its customer and operation, including the parent request for replies. Preserve the original ID when a save outcome is uncertain; never automatically register a replacement and resubmit. An expired unused ID cannot commit. A deliberate new submission requires a newly registered ID and customer confirmation.

Completed receipts follow request retention and are unaffected by unused-ID expiry. The earlier 24-hour receipt-retention proposal was separate from unused-ID validity. Purged or unknown IDs cannot create records.

Hanlin proposed 30 minutes and three IDs; David conditionally accepted them. Draft 3.1 already specifies rejection of a fourth registration. Hanlin clarifies the combined limit and no-eviction rule; David verifies registration, cleanup and commit races.

## 4. Explicit read-only account status — D16

Keep account status within C1. The customer explicitly selects **"Check my account status."** Add a requested-operation selector to the request contract; the server validates it and determines the response `route`.

Hanlin's existing `route` field is response-side, so it does not yet define how the customer selects the operation. The selector requests an action; it never supplies authority or customer scope.

Read only `customer_id` and `account_status`, using the authenticated customer's server-derived scope. Return a fixed response without retrieval or model generation. General knowledge questions need no customer lookup. Account changes go to human support; unavailable data is explained without guessing. Customer-database fields never go to the AI provider, and customer-data unavailability must not block confirmed support saving with trusted identity.

This preserves D16's narrowing of Hanlin's original four-field proposal. Hanlin defines the request selector and response examples; Collins aligns routing; David checks isolation and zero provider calls.

## 5. Release authority and backup — D08

**I am the primary release authorizer, and Hanlin is the accepted backup.** David declined the additional role. Hanlin confirmed availability in response to my request; this records the role assignment, while the technical release rules still await final team agreement.

A change requires independent review, passed evaluation and a rollback reference. Its author cannot provide final release authorization. When I author a change, an available designated non-author must authorize it. When the backup authors a change, I may authorize it if independent. If no designated non-author is available, hold release until another qualified non-author accepts and receives explicit release permission.

A qualified independent reviewer may also authorize release if designated with the required permission, avoiding an unnecessary third mandatory approver. Release only the exact version reviewed and evaluated. I or the designated backup may restore a previously approved version, recording the reason.

Independent review came from Collins's improvement flow and Hanlin's approver question. Hanlin's Draft 3.2 and David's revised verification plan now record non-author enforcement and David's decline. Hanlin aligns C6 permissions, Collins supplies the release flow, and Vlad coordinates remaining independent verification.

## 6. Support-save performance — D11/V31

At least **95% of valid, confirmed submissions** should be durably saved, with a success acknowledgement ready, within **two seconds of application receipt**.

Start timing when the application receives the final confirmed submission. End when the database commit is confirmed and the success response is ready. Exclude ID registration, form editing and human-agent response time. Measure registration separately.

Count slow saves, definite failures, **uncertain commits** and capacity rejections as misses. Report admission counts and every outcome category separately.

Count each intended submission once toward the target. Record all retry attempts separately; retries retain the original ID and do not restart its timing. Report clearly invalid, unauthorized, expired-ID and conflicting-payload attempts separately. A late reconciliation must not turn an initially untimely outcome into a timely success.

This addresses David's objection to measuring only successful saves. The target requires validation. Hanlin defines the contract and measurement boundary; David specifies the accounting and failure cases.

## 7. AI evidence-support policy — D03/C10

**Selected by Vlad on November 3:** adopt Collins's conservative, extractive evidence policy for the prototype, with the following contract refinements. Final integrated team approval remains pending.

Use a reviewed, versioned manifest of exact normalized question aliases, required source versions/excerpts and approved answers. Require one matching active intent, all required authorized evidence and an exact normalized approved-answer match, with no additional wording. Preserve case, numbers, punctuation and negation. Do not add fuzzy acceptance, another model call or automatic generation retry.

Bind an immutable evidence expectation to each inquiry before generation: policy/manifest version, intent ID, approved answer and required source references/excerpt spans. Pass this explicitly to C10; never infer the expectation from candidate output or use shared mutable inquiry state. Keep customer/session data outside the provider request. Missing, unavailable or failed checking suppresses the candidate and offers clarification or support; saving support still requires customer confirmation.

Accept the limited FAQ coverage for the prototype: the model produces constrained evidence wording rather than free-form synthesis. Unlisted questions and paraphrased answers may fall back. This restriction does not establish general semantic correctness. The manifest must be supplied and independently reviewed before activation; absent it, fail closed. Keep B12 manual evaluation separate. Eligibility is fixed before testing; eligible alias misses and rejected paraphrases remain service-target misses.

Hanlin aligns C10's typed expectation and outcomes. Collins supplies the manifest, normalization/excerpt rules and coordinator handoff. Vlad coordinates independent fixture review. Implementation and measured quality remain pending.

## 8. Prototype and production circuit breakers — D14/V18

**Selected by Vlad on November 3:** retain the following prototype defaults and provisional production candidate, incorporating Collins's shared-state rules. Final team approval and measured validation remain pending.

**Prototype:** retain three consecutive qualifying failures within 60 seconds; successful provider calls reset that sequence.

**Production candidate:** evaluate opening on **at least 50% qualifying failures among completed provider calls in a rolling ten-second window, after at least 20 calls have completed**. These values remain provisional; Collins's specification is received and independent validation remains pending.

Both proposals retain:

- A 30-second cooldown.
- One recovery trial shared across application instances.
- A 20-second trial lease.
- Shared PostgreSQL coordination scoped to provider/model/credential configuration, without holding a database lock during the provider call.

The production window replaces consecutive-failure counting; an ordinary successful call contributes to the window rather than resetting it. Collins must define window updates, recovery resets, stale-result handling, expired leases and qualifying failures. Already-admitted calls may finish; obsolete results must not change a newer breaker state.

Respect provider quota-reset guidance. Customer validation failures, unsupported questions and semantic rejections are not provider outages. Exhausted daily/monthly quota is not probed every 30 seconds. Credential/configuration errors require correction. Failed inquiries are not automatically resubmitted.

The rate-based production candidate is a new refinement, not a teammate-selected threshold. Sliding windows with minimum call volumes are a documented approach, but that does not validate our exact settings. [Circuit-breaker reference](https://resilience4j.readme.io/docs/circuitbreaker).

### Counting, recovery and response rules

Use unique completed-call IDs, database completion times and state epochs to count each provider outcome once. A well-formed provider response is an availability success even when C10 rejects its content: include it in the production denominator, exclude it from qualifying failures, and retain it as an AI-service miss. Prototype successes reset the consecutive sequence; production successes contribute to the rolling window.

Keep one globally leased trial on a new admitted inquiry, with no database lock held during the external call. Ignore obsolete-epoch completions for breaker state, recover expired leases and fail closed when shared coordination is unavailable. The lease never extends the provider or inquiry deadline. Respect longer Retry-After/reset guidance; disable exhausted quota or invalid configuration rather than probing every 30 seconds. No automatic inquiry replay.

Before admission, return 503 SERVICE_BUSY with Retry-After for admission denial. After admission, C3 circuit_open/provider failure returns controlled 200 temporarily_unavailable with a support option. Overall-deadline expiry returns 504. Otherwise-eligible no-answer outcomes remain misses against the separate AI-service objective. Collins and Hanlin align their flows/contracts; resource contention and recovery checks remain planned.

## 9. Retention and deletion — D09

| Data | Proposed retention |
| --- | --- |
| General chat transcripts | Do not persist |
| Minimal inquiry metadata and linked feedback | 30 days from inquiry creation |
| Sanitized diagnostic logs | Seven days; exclude raw content, credentials and direct customer identifiers |
| Confirmed support content, replies and completed receipts | While open, plus 30 days after resolution |
| Minimal support-action audit records | Follow the associated support request |
| Evaluation/release summaries | Retain for active and retained rollback versions, then 30 days after the associated version is retired |
| Encrypted daily backups | Seven-day rotation |

Block access at retention expiry. Purge expired live records during the next daily cleanup, within 24 hours. Remove linked feedback with its inquiry metadata. Review old open requests rather than automatically deleting unresolved work.

Keep raw conversations and feedback out of audit and evaluation summaries. Track live-record deletion separately from backup expiry. Before restored data becomes available, reapply current expiry rules and recorded deletions. Provider-held copies follow the selected provider's documented policy, supplied by Collins.

Hanlin aligns V11/V21/V32/V33 and the related contracts; David verifies actual deletion, restricted access, receipt protection, backup expiry and restoration. Provider retention remains evidence-dependent.

## 10. Provider choice and production capacity — D13

Evaluate Cohere first and compare Groq using the same questions before choosing an exact model.

Treat free evaluation access as prototype-only. Cohere lists 20 trial chat requests per minute and 1,000 calls per month. Several listed production models allow 500 requests per minute, still below our one-call-per-inquiry planning case of 10,000 per minute. A paid key alone does not establish sufficient capacity. [Cohere limits](https://docs.cohere.com/v2/docs/rate-limits).

Collins supplies model/account quotas, token budgets, permitted data, retention settings, latency evidence and a production capacity/cost proposal. Additional evidence-checking calls must be included. A smaller model-call fraction requires justification.

Keep prototype traffic fictional and simulated application-load results separate from live-provider compatibility checks. Automatic second-provider failover remains deferred. Production capacity and any service purchase remain separate decisions requiring evidence and team agreement.

## 11. Accounts, roles and company scope — D07/D18

Start with **one company** and controlled account provisioning through a protected management command or approved bulk import. Use fictional accounts for the prototype; provide no public self-registration or role-selection screen.

Map customer accounts to approved customer identifiers from the existing customer database. Keep authentication credentials, password hashes and roles in the application's controlled account store. C7 remains read-only. Credentials do not belong in the public repository.

| Role | Permitted access |
| --- | --- |
| Customer | Their own inquiries, status, support requests and feedback |
| Agent | Unassigned support work and requests assigned to them |
| Administrator | Knowledge-document administration; no automatic support-content or feedback access |

Assign reviewer and release permissions explicitly. Check role and object ownership server-side on protected requests. Role/permission changes revoke existing sessions. Hanlin specifies provisioning and permission contracts; David verifies denial and role-change cases.

## 12. Fixed test questions and fair measurement — D20

Preserve the B12 baseline: **12 supported, four unsupported and four ambiguous questions**. Retain its existing quality gates separately from production service targets.

Before testing, record classifications, expected outcomes and supporting source versions. Another qualified member reviews the labels. David owns the identified test-set version.

Otherwise-eligible AI questions remain in performance results when they fail, time out or receive busy responses. Report account-status checks, explicit human requests and unsupported questions separately. An eligibility label must not be reassigned after an unsuccessful result to improve the percentage.

Keep the small quality baseline separate from production-load testing. The proposed AI service target remains at least 95% of all eligible inquiries received returning supported answers within 15 seconds at the selected workload. Structural citation checks alone do not establish a supported answer.

## 13. Workload and concurrency limits — D01/D11/D20

Retain these proposed scenarios:

- Baseline: approximately **166.67 inquiries/second**, initially for ten minutes in controlled load validation.
- Two-minute peak: **333.33/second**, a peak factor of two.
- Separate overload case: **10,000 arrivals within one second**.

These follow the selected assumption of 10,000 active sessions averaging one inquiry per customer per minute; they are not measured capacity.

Prototype generation concurrency may be **up to five**, only where account/model limits permit. Also enforce request and token budgets. Apply an aggregate concurrency limit across instances, with no AI waiting queue and an immediate controlled busy outcome when admission is unavailable.

Leave the production limit pending provider quotas, measured service times and resource evidence. Illustrative in-flight calculations are not safe configuration limits. Keep support-save/status admission separately bounded. Hanlin aligns V14/V15; Collins supplies quotas; David defines measurements and stop conditions; I review the resulting production assumptions.

## 14. Deadline and fallback timing — D04/D11/V28

Keep a **20-second overall deadline**, a provider wait of at most **12 seconds**, and a **one-second fallback reserve**. Shorten provider/dependency waits when the remaining budget requires it.

Return fallback immediately when failure is known. Stop waiting on dependencies by approximately second 19.

Use 200 `temporarily_unavailable` for a delivered controlled provider-unavailable outcome, 504 `DEADLINE_EXCEEDED` when the overall deadline expires and a response can still be sent, and 503 `SERVICE_BUSY` for aggregate admission overload. Preserve the distinct evidence-validation outcomes in C10.

Ignore late results and never create support requests automatically. An otherwise-eligible AI fallback remains a service-target miss.

The **95%-within-15-seconds target** is separate from the 20-second hard deadline. A 12-second provider call leaves only three seconds for other work to meet that target; the timeout settings do not prove performance. Collins confirms V28 and the outcome mapping; Hanlin aligns the contract; David verifies timeout and late-result cases.

## Responsibilities and final review

**Responses are due Tuesday, November 3, 2026, at 10:00 a.m. Eastern.** Use the D-number, remaining concern, suggested wording and supporting evidence in your existing issue or section PR.

| Person | Required follow-up |
| --- | --- |
| Vlad — [#11](https://github.com/vlad8110/deskguide/issues/11) | Review cross-component findings and coordinate one consistent final document, diagram, contracts and rationale after the response cutoff |
| Hanlin — [#12](https://github.com/vlad8110/deskguide/issues/12), [PR #17](https://github.com/vlad8110/deskguide/pull/17) | Align state names, session/ID values, combined ID limit, explicit account-status selector, provisioning/permissions, release authority and measurement contracts |
| Collins — [#13](https://github.com/vlad8110/deskguide/issues/13), [PR #16](https://github.com/vlad8110/deskguide/pull/16) | Supply provider evidence, evidence-support rules, production-breaker details and timing confirmation |
| David — [#14](https://github.com/vlad8110/deskguide/issues/14), [PR #18](https://github.com/vlad8110/deskguide/pull/18) | Revised verification and review responses posted; backup role declined. Vlad coordinates remaining urgent review coverage |
| All four members | Review the same identified final document, diagram, contracts and rationale |

Final team approval remains pending. Unanswered technical items remain open after the response cutoff.
