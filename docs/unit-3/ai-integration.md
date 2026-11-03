# AI integration, escalation and feedback — revised design specification

**Lead:** Collins Amponsah
**Reviewers:** Hanlin Wang and David Warren
**Architecture coordination:** Vladimyr Merci
**Revision:** November 3, 2026; aligned to Hanlin's Interface Contracts Draft 3.2 and Vlad's November 2 Revised Proposed Decisions.

**Status:** Revised design proposal for review. Team acceptance remains pending. No application implementation, executed tests, live provider access, measured answer quality or production capacity is claimed.

The alignment below uses the copies reviewed for this revision. Final approval must identify the exact reviewed commits and final combined document. Subsequent changes require another consistency check.

## 1. Purpose, architecture and boundaries

DeskGuide answers basic customer-service questions from permitted knowledge sources, offers customer-confirmed human support, and uses feedback through a reviewed improvement process.

The proposed deployment is a modular Flask application replicated behind HTTPS ingress, with shared PostgreSQL persistence. Logical modules do not imply independently deployed microservices.

The model cannot authorize access, query customer databases, save support requests, change accounts or release improvements. Application components enforce these responsibilities.

The initial scope is one company with controlled account provisioning. Multi-company support, public registration, automatic model retraining and automatic second-provider failover are deferred.

All examples and evaluation fixtures are fictional. Real customer content and credentials must not enter the public repository.

## 2. Components and contract mapping

| Module | Responsibility | Contracts |
|---|---|---|
| M1 Browser interfaces | Questions, account-status selection, citations, consent, support submissions and replies, feedback | Calls C1, C2b, C4a–C4e, C5, C6, C8 and C9b as permitted |
| M2 InquiryService and AccessControl | Authentication, authorization, routing and orchestration | C1, C9a–C9c |
| M3 Retriever and DocumentService | Permitted evidence, source versions and document administration | C2, C8 |
| M4 GenerationAdapter | Provider translation, budgets, normalized failures and shared breaker coordination | C3 |
| M5 AnswerValidator | Citation, access, version and runtime support checks | C10 |
| M6 EscalationService and AgentQueueService | Registered IDs, durable requests, receipts, customer replies and agent workflow | C4, C5 |
| M7 CustomerDirectoryAdapter | Read-only, scoped customer-data access | C7 |
| M8 FeedbackService | Feedback, independent review, evaluation, release and rollback | C6 |
| M9 Persistence adapters | Shared sessions, accounts, receipts, support records, configuration and breaker coordination | Supports owning modules |

Hanlin's interface-contracts.md defines endpoint schemas, method signatures and shared error envelopes. This document defines the integration sequences and AI policies.

C4 subcontracts are:
- C4a: register an escalation submission ID.
- C4b: submit the confirmed escalation.
- C4c: reconcile status using an escalation or reply submission ID.
- C4d: register a customer reply ID.
- C4e: submit the customer reply.

C9a supplies internal AccessContext; C9b supplies session endpoints; C9c defines controlled provisioning and permissions.

C3 intentionally has no AccessContext parameter. Authorization occurs before generation, and identity or session context never reaches the provider.

## 3. Shared authorization, identifiers and privacy

### Authentication and access

Use opaque server-side cookie sessions with Secure, HttpOnly and SameSite=Lax attributes. State-changing requests require a valid session-bound CSRF token.

Proposed session limits are 30 minutes of inactivity and eight hours absolute. Authenticated activity renews only inactivity expiry. Login rotates the session identifier. Logout invalidates the current session. Role or permission changes revoke existing sessions across replicas.

The server derives identity, role and object scope. Browser-supplied identity, role or scope never grants access.

Customers access their own records. Agents access unassigned support work and their own assignments. Document-administrator privileges do not automatically grant support-content, feedback or release access.

### Identifiers

| Identifier | Rule |
|---|---|
| correlation_id | Server-generated tracing identifier |
| inquiry_id | Server-generated inquiry reference |
| answer_id | Server-controlled answer reference; null when no answer is returned |
| submission_id | Server-issued, registered and bound to customer and operation; replies also bind to parent request |
| request_id | Durably saved support request |
| SourceRef | Exact source_id, section_id and source_version |
| configuration_version | Versioned retrieval, prompt, model and support-policy configuration |

Unused submission IDs expire 30 minutes after registration. A customer may hold at most three unused, unexpired IDs combined across escalation and reply operations.

A fourth registration returns 429 RATE_LIMITED and evicts nothing. Enforce the cap atomically across replicas. Expired IDs free their slots even before cleanup.

Completed receipts follow support-record retention; unused-ID expiry never removes them. Unknown, foreign or purged IDs cannot create records.

### Provider data boundary

C7 reads only customer_id and account_status for authorized operations. Customer-database fields never enter C3 or the provider payload.

Generation uses the question and permitted knowledge passages, with a fixed application-controlled instruction template. Provider credentials are transport credentials held server-side, never prompt content.

Do not forward AccessContext, session credentials, CSRF tokens, customer records, support content or raw feedback. Correlation and configuration metadata remain internal unless an explicit provider integration requirement is reviewed.

User text may itself contain personal information. The interface should discourage sensitive input; provider selection and data-use review must address this remaining exposure. General chat transcripts are not persisted.

Retrieved instructions and customer text are untrusted data. They cannot change authorization, grant tools or override application policy.

## 4. Flow A — inquiry routing and supported answers

Contracts: C1, C2, C3, C7, C9 and C10.

1. Authenticate the session, validate CSRF and validate C1 input.
2. Build trusted authorization context and assign inquiry/correlation identifiers.
3. Validate requested_operation and set the response route before admission.
4. Apply applicable customer limits and separately bounded route admission.

### Account-status route

The customer explicitly selects check_account_status. A question field must be absent.

1. Derive customer scope server-side.
2. Call C7 for customer_id and account_status only.
3. Return a fixed application template with route account_status and answer_origin account_status.
4. Make zero retrieval calls and zero model calls.
5. If customer data is unavailable, state that status cannot be checked and offer support without guessing.

Account changes require human support. General knowledge questions need no customer lookup. A C7 outage does not prevent confirmed support saving using trusted identity.

### General knowledge route

For requested_operation ask_question:

1. Recognize an explicit human request under a bounded application policy; offer support without generation.
2. Otherwise set route ai and apply AI admission.
3. Retrieve permitted passages through C2a.
4. Apply the pre-generation evidence policy in Section 5.
5. If it passes, construct C3 GenerationRequest with no customer-data or AccessContext fields.
6. Make at most one generation call.
7. Validate the candidate through C10, including runtime support checking.
8. Return only a passing answer, with exact versioned citations resolvable through C2b.
9. Suppress a failed candidate and offer clarification or customer-confirmed support.

Retrieval failure is service unavailability, not evidence that no source exists. Citation access is rechecked when a source is opened.

Match browser responses to inquiry_id so late results cannot overwrite a newer inquiry.

## 5. Proposed executable evidence policy — D03 / V19 / C10

**Proposal for team review:** a deliberately conservative, extractive prototype policy. This defines an implementable rule without assuming an unvalidated semantic model can prove factual support.

It limits accepted AI output to reviewed evidence wording. It does not establish general semantic correctness or measured answer quality.

### 5.1 Versioned evidence manifest

Maintain a reviewed manifest tied to exact source versions and the support-policy version. Each supported intent contains:

- A unique intent identifier.
- Explicit normalized question aliases.
- Required SourceRefs.
- One approved answer text assembled from exact, contiguous source excerpts.
- The source and character range of each excerpt.
- Review status and any retired or conflicting-source flag.

Aliases, excerpts and labels must be reviewed before activation. They cannot be created automatically from user feedback or model output.

Normalization is Unicode NFC, trimming and collapsing whitespace. Preserve case, numbers, punctuation and negation. Do not use fuzzy or embedding similarity as an acceptance threshold in this prototype.

The manifest contains permitted knowledge content only, with no customer records or interaction transcripts.

### 5.2 Pre-generation evidence sufficiency

Inputs: question, authorized retrieved passages and the active reviewed manifest.

A question is sufficient only when:
1. Its normalized form exactly matches an alias for exactly one active intent.
2. Every required source/version is present in the authorized retrieved set.
3. All required excerpts still match their source character ranges.
4. No required source is retired, conflicting or inaccessible.
5. The full required evidence fits the provider input budget.

Thresholds:
- Exactly one matching intent.
- 100% of required references and excerpts present.
- Zero unresolved access, version or conflict conditions.

No match, multiple matches, missing evidence or an unreviewed intent prevents generation. Offer clarification or support.

If the manifest or check cannot run, fail closed and report the check as unavailable. Do not treat an infrastructure error as a genuinely unsupported question for performance accounting.

### 5.3 Runtime answer support

The coordinator selects the expected approved answer before C3 and binds that selection to the inquiry. It does not infer the intended answer from the model's output.

C10 first performs its structural checks: citation membership, exact versions, access, resolution, output format and at least one citation.

The configured EvidenceSupportPolicy receives candidate text, cited passages and the immutable EvidenceExpectation defined in C10 (inquiry_id, policy/manifest versions, intent, approved answer and required source spans). M2 binds it before C3 and verifies inquiry identity; no expectation is derived from model output or stored in shared mutable inquiry state. It contains permitted knowledge only and is not a provider payload field. Source spans use zero-based Unicode code-point [start,end) offsets into the NFC-normalized immutable section text, without collapsing source whitespace. It checks:
1. Normalized candidate text exactly equals the approved answer selected for this inquiry.
2. Every approved excerpt is still present in the cited evidence.
3. No additional wording, number, instruction or qualification was introduced.

Acceptance threshold is 100% approved-text match, with zero additional content. The coordinator separately verifies that cited references cover the selected manifest entry.

A text mismatch returns unsupported_content. When precise unsupported spans cannot be isolated, identify the whole candidate as unsupported. A missing policy, manifest, timeout or checker error returns support_check_unavailable.

No additional provider call is made for either check. Model confidence is ignored. A failed candidate is suppressed; generation is not retried.

### 5.4 Limits and review conditions

Exact extraction can still reproduce incorrect or misleading source material. Independent source review and B12 manual evaluation remain necessary.

The policy intentionally rejects paraphrases and unlisted questions, reducing coverage. A future semantic policy requires a new version, reviewed thresholds, adversarial evaluation and explicit provider/deadline accounting.

The manifest, aliases and source labels have not been supplied or tested in this revision. Until configured and reviewed, the rule remains unavailable and AI answers fail closed. This is not completed supported-answer functionality or proof of meeting the service target.

## 6. Flow B — confirmed human handoff and replies

Contracts: C4a–C4e and C5.

### New support request

1. Explain the limitation or acknowledge the human request.
2. Let the customer review/edit the content and optional note.
3. Explain sharing and require explicit consent.
4. Register a server-issued escalation ID through C4a.
5. Submit the reviewed content through C4b with the same ID and consent_to_share true.
6. Validate ownership, operation, expiry and content.
7. Atomically save the request, complete the receipt and enforce uniqueness.
8. Acknowledge only after durable commit, returning request_id and submission_id.
9. Make the request available to authorized agents through C5.

Registration alone creates no human-visible support request. An acknowledgement means saved, not read by an agent, and promises no human response time.

### Agent workflow

An agent sees unassigned requests and their own assignments only.

Permitted progression:
- queued → assigned through atomic claim.
- assigned → in_review.
- in_review → waiting_for_customer with a customer-visible message.
- waiting_for_customer → in_review through a valid customer reply, retaining the owner, or the assigned agent.
- in_review → resolved.
- assigned, in_review or waiting_for_customer → queued through owner release with release_reason; clear ownership.
- resolved is terminal.

State changes require atomic ownership/version checks. Conflicts never silently overwrite another update.

### Customer reply

1. Customer opens their own waiting_for_customer request.
2. C4d registers a reply submission ID bound to customer, operation and parent request.
3. C4e submits message and expected_version.
4. In one transaction, check ownership/state/version, save the reply, complete its receipt, retain the assigned agent, move to in_review and increment version.
5. A same-ID/same-payload replay returns the original reply without another state change.
6. A late reply or resolution race cannot reopen a resolved request.

Attachments, notification email, live chat and reopening are outside this draft.

## 7. Flow C — provider failures and deadlines

Contracts: C1 and C3; C4 only after customer confirmation.

Provider-neutral categories:
- timeout.
- quota_exceeded.
- service_unavailable.
- invalid_provider_response.
- circuit_open.
- provider_configuration_error.

Before calling the provider, check admission, quota budget, breaker state and remaining time.

**V17:** zero automatic generation retries. SDK or transport retry defaults must be disabled or accounted for so they cannot silently create extra generation attempts. Automatic second-provider failover remains deferred.

**V28 confirmation:**
- Overall hard deadline: 20 seconds from application receipt.
- Provider wait: at most 12 seconds.
- Fallback reserve: one second.
- Shorten every dependency wait to fit the remaining budget.
- Stop dependency waiting by approximately second 19.
- Return fallback immediately when failure is known.

| Condition | Outcome |
|---|---|
| Aggregate admission unavailable | Immediate 503 SERVICE_BUSY with Retry-After; no queue |
| Admitted inquiry encounters a provider failure, including circuit_open | Controlled 200 temporarily_unavailable with support offered |
| C10 support or structural check fails | Controlled clarification/escalation outcome; candidate suppressed |
| Overall deadline expires and a response can still be sent | 504 DEADLINE_EXCEEDED |

A breaker denial discovered during AI admission may use the admission 503 path; a C3 circuit_open result after admission uses the controlled 200 path. Vlad selected this stage distinction on November 3; C1/C3 must use the same mapping.

Late results cannot replace a completed response or create a support request. Browser question text remains in the active view. No persistence across reload is promised.

A controlled 200 fallback is not a supported AI answer and remains a miss for an otherwise-eligible inquiry.

## 8. Flow D — uncertain saving and duplicate-safe recovery

| Situation | Behavior |
|---|---|
| Validation fails | Preserve content; show safe field guidance; no receipt claimed |
| Save definitely failed | 503 DEPENDENCY_UNAVAILABLE; state nothing saved; same-ID retry while valid |
| Commit outcome unknown | 503 SAVE_OUTCOME_UNCERTAIN; do not claim nothing saved |
| Response lost after commit | Reconcile through C4c or same-ID/same-payload retry |
| Completed receipt and same payload | Replay original result; no new request/reply |
| Completed receipt and changed payload | 409 CONFLICT |
| Expired unused ID | 410 SUBMISSION_ID_EXPIRED; cannot commit |
| Unknown, foreign, wrong-operation or purged ID | 404 NOT_FOUND; cannot create records |
| Fourth unused-ID registration | 429 RATE_LIMITED; no eviction |
| Deliberate new submission | New server registration and customer confirmation |

For uncertain outcomes, preserve the original ID and payload. Never automatically register a replacement and resubmit.

Receipt lookup precedes unused-expiry handling for completed submissions. Completed receipts remain replayable within their retention even after the original unused-ID validity period.

Request/reply data and its receipt commit together in shared storage. A disabled button is not duplicate protection.

If a queue broker is introduced, use a transactional outbox or equivalent recovery mechanism. Shared durable request storage remains authoritative.

## 9. Flow E — feedback, release and rollback

Contracts: C6, C8 and controlled M3/M4 configuration changes.

1. Customer submits inquiry_id, rating and optional permitted category/comment.
2. C6 verifies ownership and derives outcome, route and configuration from trusted metadata.
3. Feedback is accepted even when no answer exists; no client answer_id is required.
4. A staff member with reviewer permission examines permitted feedback.
5. Propose a bounded knowledge, retrieval, prompt or configuration change.
6. A different qualified reviewer approves it for evaluation or rejects it.
7. Evaluate the exact candidate version against the locked B12 baseline.
8. Record baseline version, source versions, evaluation report and rollback reference.
9. A designated release_authorizer who is not the change author authorizes the exact reviewed and evaluated version.
10. Apply approved knowledge changes through C8/M3 and generation configuration through M4.
11. Monitor and restore a previously approved version when rollback is required, recording the reason.

An evaluated version is immutable. Any edit requires a new version, independent review and evaluation.

Vlad is primary release authorizer and Hanlin is the accepted backup. Accounts require explicit release_authorizer permission; authors cannot authorize their own release. If no available authorizer is independent, designate another qualified non-author before release.

A qualified independent reviewer may also authorize release; a third mandatory approver is not required.

Feedback cannot directly retrain the model or release changes. Raw customer feedback is not copied into public documents, source material or evaluation summaries.

## 10. Proposed circuit-breaker details — D14 / V18

These rules complete the design proposal and require team review and David's validation.

### Scope and coordination

Key breaker state by provider, exact model and credential-configuration version. Store shared state in PostgreSQL through M9.

Persist state, epoch, next permitted trial time and trial lease ownership. Use atomic short transactions for admission and state updates. Never hold a database lock during a provider call.

Each admitted provider call receives a unique call ID and breaker epoch. Record a completion at most once. State changes compare the current epoch so obsolete results cannot mutate newer state.

If shared coordination cannot be obtained, fail closed to controlled unavailability. Do not fall back to independent per-replica unlimited calls.

### Qualifying outcomes

Count as qualifying failures:
- Provider/network timeout after a dispatched call.
- Connection failure.
- Provider 5xx.
- A transient provider 429.
- Malformed, truncated or otherwise off-contract provider output.

A valid provider response declining to answer counts as transport success, not proof of answer support.

Do not count as qualifying provider failures:
- Invalid or unauthorized customer requests.
- Insufficient evidence.
- C10 semantic rejection.
- Admission rejection.
- Cancellation before dispatch.
- Shared-state failures before dispatch.

Credential/configuration errors and exhausted daily/monthly quota enter a separate disabled-until-corrected-or-reset condition. They do not trigger routine 30-second probes. Respect a longer provider Retry-After or documented reset time.

### Prototype counting

While closed, open on three consecutive qualifying failures whose completion times fit within 60 seconds.

A successful provider call resets the sequence. A failure outside the retained 60-second sequence starts a new sequence. Use shared database time and a defined transaction order for concurrent completions.

### Production candidate counting

While closed:
1. Store one outcome per completed provider call for the current epoch.
2. Use database-recorded completion times.
3. Retain outcomes in the rolling interval (now minus 10 seconds, now].
4. Compute total completed provider calls N and qualifying failures F.
5. Open only if N is at least 20 and F/N is at least 0.50.

Every well-formed completed provider response contributes to N as an availability success, even when C10 rejects its content. Semantic rejection is excluded from F, not removed from N, and remains an AI-service miss. Pre-dispatch denials are not completed provider calls. Successful calls contribute to N and do not reset the window. Completions from older epochs are excluded.

These thresholds are provisional, not validated production settings.

### Opening and recovery

On opening, atomically advance the epoch and set the next trial time to at least 30 seconds later, extended by applicable quota guidance.

Already-dispatched calls may finish for their original inquiries within their deadlines. Their old-epoch outcomes cannot close the breaker or modify the new window.

After cooldown:
1. One newly admitted inquiry acquires the shared recovery trial using an atomic lease.
2. The lease lasts 20 seconds and carries a new epoch.
3. Other inquiries receive circuit_open; none wait in an AI queue.
4. A successful, well-formed provider response under the current live lease closes the breaker.
5. Closing advances the epoch, clears prototype counters and production-window history, and removes the lease.
6. A qualifying trial failure reopens it with a new cooldown.
7. A configuration or exhausted-quota result applies the corresponding disabled condition.
8. An expired or abandoned lease reopens with a cooldown and invalidates that epoch.
9. A late trial result cannot close a newer epoch.

A half-open call still uses the at-most-12-second provider wait and the inquiry's remaining deadline; the lease does not extend either deadline.

A recovery success concerns provider availability only. C10 must still validate the candidate before any answer is shown.

Failed customer inquiries are never automatically resubmitted.

## 11. Provider budgets, workload and honest measurement

### Working budget

Follow the proposed V30 ceiling of 4,096 total input tokens and 512 output tokens, subject to exact-model verification.

Count instructions, question, evidence and provider framing in the input budget. Do not silently alter an oversized question.

Select permitted evidence that fits. If any manifest-required evidence is omitted, rerun sufficiency and fail closed rather than generating from an incomplete required set.

Prototype concurrency is up to five only when the account's request and token quotas permit it. A concurrency ceiling alone does not enforce requests-per-minute or token limits.

No AI waiting queue is permitted. Capacity exhaustion produces immediate admission rejection. Support save/status have independent bounds.

### Workload assumptions

| Scenario | Proposed offered load |
|---|---|
| Baseline | 166.67 inquiries/second for 10 minutes |
| Peak | 333.33 inquiries/second for 2 minutes |
| Overload | 10,000 arrivals within one second |

These derive from 10,000 sessions averaging one inquiry per minute; they are planning assumptions.

At generation fraction f and one generation call per admitted AI inquiry:
- Baseline provider demand is approximately 10,000 × f calls/minute.
- Peak demand is approximately 20,000 × f calls/minute.
- Additional provider-based checks would increase demand; this proposed evidence policy adds none.

Do not choose f merely to fit an available quota. Justify it using independently labeled workload composition.

Production request/token quotas, concurrency and cost remain unresolved. Simulated application-load tests cannot establish live-provider capacity.

### Service targets

AI: at least 95% of eligible inquiries return supported answers within 15 seconds, pending evidence.

Fix synthetic eligibility and expected outcomes before testing. Busy outcomes, timeouts, validation failures and fallbacks remain misses for otherwise-eligible inquiries. Do not relabel a failed question to improve the denominator.

Report account-status operations, explicit human requests and genuinely unsupported questions separately.

Support saving: at least 95% of valid confirmed submissions are durably saved with acknowledgement ready within two seconds from application receipt.

Count each intended submission once. Retries retain the original ID and original first-submit timing. Slow saves, uncertain commits, definite failures and capacity rejection are misses. Measure ID registration separately. Late reconciliation cannot convert a miss into a timely success.

### Provider evidence still required — D13 / V15 / V30

Evaluate Cohere first and compare Groq before selecting an exact model. No provider/model is selected by this revision.

The final evidence record must identify:
- Exact model, account tier, access date and official policy sources.
- Request and token quotas, burst/concurrency limits and reset guidance.
- Input/output bounds and tokenizer.
- Data retention, training use, deletion and available privacy settings.
- Measured latency with the intended prompt/evidence sizes.
- Baseline/peak capacity and cost proposal.

Vlad's supplied quota figures are planning references, not independently verified account entitlements in this revision. Free evaluation access does not demonstrate production suitability. No purchase or activation is authorized by this document.

## 12. Retention and logging

| Data | Proposed retention |
|---|---|
| General chat transcripts | Not persisted |
| Minimal inquiry metadata and linked feedback | 30 days from inquiry creation |
| Sanitized diagnostic logs | 7 days |
| Confirmed support content, replies and completed receipts | While open, plus 30 days after resolution |
| Minimal support-action audit records | Follow the support request |
| Evaluation/release summaries | Active and retained rollback versions, then 30 days after retirement |
| Encrypted daily backups | 7-day rotation |

Block access at expiry. Purge expired live records at the next daily cleanup within 24 hours. Review old unresolved requests rather than automatically deleting them.

Remove linked feedback with expired inquiry metadata. Keep raw conversations and feedback out of audit/evaluation summaries.

Track live deletion separately from backup expiry. Reapply current expiry rules and recorded deletions before restored data becomes accessible.

Diagnostic logs may contain correlation_id, normalized error category, duration and configuration_version. Do not log raw questions, answers, passages, notes, feedback, session identifiers, CSRF tokens, credentials, direct customer identifiers or raw provider errors.

Any permitted audit identity must use the separately reviewed access-controlled audit policy. Provider-held retention remains unresolved until provider evidence is reviewed.

## 13. Planned verification

No test has been executed for this revision.

| Scenario | Expected result |
|---|---|
| Explicit account-status selection | Fixed response; zero retrieval/model calls |
| Forged identity or role | No scope expansion |
| Missing CSRF, expired/revoked session | Contract-defined rejection |
| Supported manifest intent and exact approved answer | Pass only with valid current citations |
| Correct citations plus added unsupported wording | Candidate suppressed |
| Missing manifest, ambiguous alias or checker timeout | Fail closed; no unverified answer |
| Provider timeout/configuration/quota failure | Safe mapped outcome; zero automatic retries |
| AI admission exhausted | Immediate 503; no waiting queue |
| Overall deadline exceeded | 504 when deliverable; late result ignored |
| Fourth unused ID across escalation/reply | 429; no eviction |
| Expired, unknown or foreign ID | No new record |
| Commit succeeds but acknowledgement is lost | Same-ID reconciliation; one saved request |
| Concurrent same-ID submits | Exactly one durable request and receipt |
| Changed-payload retry | 409 |
| Duplicate customer reply | One stored reply; no repeated transition |
| Reply races resolution | Resolved request never revived |
| Valid reply while waiting | in_review with original agent retained |
| Agent releases from any owned state | Reason required; queued with ownership cleared |
| Other agent or administrator reads support content | Denied under contract scope |
| C7 outage during confirmed support saving | Save remains available with trusted identity |
| Malicious source instructions | No unauthorized action or policy override |
| Feedback on failed inquiry | Accepted through inquiry_id where permitted |
| Author attempts own release | Denied |
| Edit after evaluation | New version requires review/evaluation |
| Production window has 19 completions | Does not open |
| At least 20 completions, failure fraction at/above 50% | Opens |
| Production success among failures | Counts in window; does not reset it |
| Two replicas attempt recovery | Exactly one shared trial |
| Expired lease or stale trial result | Cannot mutate newer breaker state |
| Exhausted long-period quota | No routine 30-second probing |
| Expiry, cleanup and backup restoration | Expired/deleted content remains inaccessible |
| Load/performance accounting | Misses retained; retries do not restart timing |

Preserve B12's 12 supported, four unsupported and four ambiguous cases, with independently reviewed labels and source versions. Retain its quality gates separately from production service targets.

David's N01–N15 cases should be cross-referenced against this table during the final combined review; this revision does not claim that comparison has been completed.

## 14. Rationale contribution and remaining review

Separating authorization, retrieval, generation, validation, support saving and feedback gives each module a focused responsibility. Provider-specific behavior remains inside M4; other components depend on shared contracts.

A modular replicated application reduces deployment and operational complexity for junior developers compared with independently deployed services. Shared persistence is necessary for cross-replica sessions, duplicate protection and breaker coordination.

Keeping one provider behind a replaceable adapter reduces integration effort but accepts temporary AI unavailability. Independent support persistence preserves a useful recovery path.

The conservative extractive evidence policy sacrifices answer coverage and paraphrasing flexibility for an explicit, inspectable acceptance rule. Its usefulness still requires reviewed fixtures and evaluation.

This is input to the combined 500-word rationale, not a replacement for that deliverable or its authoritative citation.

### Remaining decisions

- **Collins / Hanlin / David:** review the proposed manifest-based evidence rule and C10 integration; populate and evaluate the manifest before claiming supported-answer functionality.
- **Collins / David:** review breaker qualifying outcomes, atomic counting, epochs, recovery resets and lease expiry.
- **Collins:** supply exact-model provider quota, policy, retention, latency and cost evidence.
- **Hanlin / Vlad:** confirm the admission-stage versus C3 circuit_open mapping; clarify account-status answer_id semantics if necessary.
- **Vlad:** coordinate review of the aligned contracts/flows, accepted Hanlin backup and final combined version.
- **Team:** approve the same identified final versions. Production capacity and service targets remain unproven.

Record actual authored changes and completed reviews in contributions.md without overwriting teammates' existing evidence. Keep unresolved findings and final sign-off open. Keep issue #13 open until its acceptance criteria and completion evidence have been reviewed.

**Preparation note:** This revision was prepared with AI assistance for Collins's technical review. Follow course attribution requirements in the final submission.
