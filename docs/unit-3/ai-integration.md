# AI integration and data flow — working specification

Lead: Collins Amponsah. Reviewers: Hanlin Wang and David Warren. Vladimyr Merci checks architecture consistency.

Status: First design draft for review. Component names, field names, states, and policies below are proposals pending alignment with the architecture and interface contracts. This document does not claim implementation, provider access, tested capacity, or measured answer quality.

## 1. Purpose and boundaries

DeskGuide handles basic customer-service inquiries using permitted knowledge sources, offers customer-confirmed escalation to human agents, and improves through reviewed interaction feedback.

The AI component does not directly query the customer database, authorize access, create support requests, or make administrative changes. Application services enforce these responsibilities through explicit interfaces.

This design supports the team's requirement to plan for 10,000 concurrent customers. That population is not assumed to equal 10,000 simultaneous model requests. Workload rates, provider quotas, queue limits, and capacity calculations require agreement with Vlad and David.

Examples and evaluation data are fictional or synthetic. No real customer database connection, paid service activation, or automatic model retraining is proposed here.

## 2. Components and contract mapping

These are logical responsibilities; they do not require separate deployed microservices.

| Component | Responsibility | Contracts |
|---|---|---|
| Customer interface | Collect questions; display answers, citations, failures, and escalation confirmation | C1, C4, C6 |
| Inquiry coordinator | Validate requests, enforce scope, coordinate retrieval/generation, and select the response path | C1, C2, C3, C7 |
| Retrieval/source service | Retrieve permitted passages and resolve authorized source versions | C2 |
| Generation adapter | Translate the internal generation request into provider-specific calls and normalize results/errors | C3 |
| Output validator | Check response structure, source membership, citation resolution, and evidence-support rules | C2, C3 |
| Escalation service | Persist customer-confirmed requests and provide retry-safe acknowledgments | C4 |
| Agent service | Authorize queue access, ownership, and request-state transitions | C5 |
| Feedback/review service | Store permitted feedback and manage reviewed improvement proposals | C6 |
| Customer-data adapter | Return only authorized customer fields required by the current operation | C7 |

Hanlin's interface-contracts.md remains the shared location for endpoint paths, typed signatures, field constraints, and final error names. Proposed names here must be reconciled there before approval.

## 3. Shared data and authorization rules

Proposed flow identifiers:

- correlation_id: server-generated identifier for tracing one inquiry across components.
- inquiry_id and answer_id: identifiers for an inquiry and any associated answer.
- submission_id: stable identifier for one customer-confirmed escalation submission.
- request_id: identifier of the durably saved support request.
- source_id, section_id, and source_version: references to the exact evidence used.
- configuration_version: identifies the prompt/retrieval/model configuration used for evaluation and traceability.

The server derives customer identity, role, and permitted document scope from authenticated context. Client-supplied customer or scope identifiers are never sufficient authorization.

Authorization applies to inquiry access, retrieval, citation resolution, escalation status, agent review, and feedback. Customer-specific records and cached results must remain isolated by the applicable customer or tenant boundary.

C7 exposes an allowlisted customer-data view. Credentials, authentication tokens, unrestricted database records, and unnecessary personal information must not enter C3 model requests.

## 4. Flow A — supported inquiry

Contracts: C1, C2, C3; C7 only when authorized customer context is necessary.

1. The customer interface submits a question through C1.
2. The inquiry coordinator authenticates the caller, validates the input, assigns a correlation ID, and determines permitted scope.
3. If necessary, C7 supplies only the approved customer fields required for the inquiry. Failure to obtain required context stops that path; the application does not guess customer facts.
4. The coordinator calls C2 with the question and server-derived scope.
5. C2 returns ranked permitted passages with stable source, section, and version identifiers.
6. The coordinator checks whether the evidence is sufficient for the requested answer. Missing, conflicting, stale, or irrelevant evidence may require clarification or escalation.
7. The generation adapter receives the question, permitted passages, minimal approved context, and a request deadline through C3.
8. The provider returns a structured candidate answer with references to supplied evidence.
9. The output validator checks the structure, rejects unknown source IDs, verifies source resolution and current access, and applies evidence-support checks.
10. A passing answer is returned through C1 with resolvable citations. A failed validation suppresses the candidate answer and offers clarification or escalation.

Proposed successful output includes answer_id, answer status, answer text, source references, configuration version, and correlation_id.

Source existence alone does not establish factual support. Deterministic checks can verify identifiers and access, while semantic support remains imperfect and requires evaluation against reviewed examples. A model's self-reported confidence is not proof.

Retrieved documents and customer text are untrusted data. Instructions embedded in them must not override application policy or grant tools, database access, or additional permissions.

Exit states: supported answer displayed; clarification requested; escalation offered; or a controlled validation/dependency error.

## 5. Flow B — unsupported or complex inquiry and human handoff

Contracts: C1, C4, C5.

Escalation is offered when evidence is insufficient, the request requires human judgment or action, validation fails, or the customer requests human assistance.

1. DeskGuide states the limitation without displaying an unsupported answer.
2. The customer reviews and may edit the proposed escalation content. The original question is available for inclusion, but unrelated conversation history is not attached automatically.
3. The interface explains what information will be shared and requires explicit submission.
4. The interface assigns a submission_id for that intentional submission and reuses it for retries.
5. C4 validates authorization and the reviewed content.
6. The escalation service commits the support request and its idempotency record durably.
7. Only after that commit does C4 acknowledge receipt with request_id, submission_id, saved status, and creation time.
8. The authorized agent queue exposes the saved request through C5.
9. An authorized agent claims and reviews it, requests further information if necessary, and records progress or resolution.

Proposed stored fields include the reviewed content, authorized customer reference, escalation reason, originating inquiry reference, submission_id, timestamps, request state, and assigned agent where applicable.

A saved acknowledgment means the request was recorded. It does not mean an agent has read it or guarantee a response time.

Proposed agent states are queued, assigned, in_review, waiting_for_customer, and resolved. Hanlin and David must review permitted transitions and ownership rules. Concurrent claims or updates require an atomic ownership/version check; conflicting updates must not silently overwrite each other.

If a separate queue broker is used, the durable request remains the source of truth. A transactional outbox or equivalent recovery mechanism must prevent a saved request from disappearing between database commit and queue publication.

Exit states: customer declines submission; request acknowledged and queued; request awaits recovery; or submission fails with an accurate message.

## 6. Flow C — provider timeout, quota, or service failure

Contracts: C1, C3; C4 if the customer chooses escalation.

The generation adapter presents a provider-neutral result to the inquiry coordinator. Proposed internal failure categories are timeout, quota_exceeded, service_unavailable, and invalid_provider_response.

1. Check admission limits and the remaining request deadline before calling the provider.
2. Bound the provider call by the remaining deadline.
3. Map provider-specific failures into the shared internal categories.
4. Stop waiting when the deadline expires and prevent late results from replacing the completed fallback response.
5. Return a safe customer message and preserve the question in the current view.
6. Offer customer-confirmed escalation through C4.
7. Record permitted operational metadata for diagnosis.

Provider failure does not trigger an unsupported answer or automatic handoff to another provider. B17 remains consolidated into B11; second-provider failover is deferred.

Do not retry indefinitely. Any transient retry must fit the overall deadline, respect provider retry guidance, and remain within an agreed retry budget. Authentication/configuration failures require operator attention rather than repeated customer retries.

Logs may contain correlation ID, normalized error category, duration, configuration version, and retry count. Raw provider errors, credentials, and unnecessary customer content must not be exposed to the customer.

Exit states: controlled failure with escalation available, or a successful response completed within the approved retry/deadline policy.

## 7. Flow D — escalation save failure and duplicate retry

Contract: C4; C5 for subsequent review.

| Situation | Required behavior |
|---|---|
| Validation fails before saving | Show field-level guidance; preserve reviewed content; do not claim receipt |
| Save is known to fail | State that the request was not saved; allow retry with the same submission ID |
| Save succeeds but acknowledgment is lost | Show that confirmation is pending; retry or check status using the same submission ID |
| Same ID and same content are retried | Return the existing request and acknowledgment; do not create another request |
| Same ID is reused with different content | Return a conflict; require a deliberate new submission or defined correction operation |
| A separate intentional request is submitted | Create a new submission ID |

Enforce uniqueness atomically in shared durable storage using an agreed scope such as tenant/customer plus submission_id. The idempotency record and request must commit together.

A disabled submit button helps prevent accidental clicks but is not the duplicate-prevention mechanism. Concurrent application instances must rely on shared storage constraints.

The customer interface retains unsent content in the active view. Longer-term browser storage requires an explicit privacy decision. Idempotency-record retention must cover the agreed retry window; the final duration remains open.

Exit states: one saved request returned, an actionable validation/conflict error, a confirmed save failure, or an explicitly uncertain state pending reconciliation.

## 8. Flow E — reviewed feedback and improvement

Contract: C6, with controlled changes to C2/C3 configuration.

1. A customer submits permitted feedback linked to an answer or inquiry.
2. C6 verifies ownership/access and validates rating, category, and optional comment fields.
3. Store the feedback with relevant answer, source, and configuration versions.
4. Authorized reviewers examine patterns such as unsupported claims, missing knowledge, poor retrieval, unclear wording, and excessive escalation.
5. A reviewer proposes a bounded knowledge-source, retrieval, prompt, or configuration change.
6. An independent authorized reviewer checks the proposal and its privacy implications.
7. Evaluate the candidate against a fixed baseline containing supported, unsupported, ambiguous, unauthorized, and failure cases.
8. Release an approved version with recorded changes and a rollback reference, or reject the proposal.
9. Monitor the released version and roll back if agreed quality or safety criteria regress.

Feedback is evidence for review, not an instruction to the model and not an automatic training signal. A malicious or mistaken rating must not directly change production behavior.

Aggregate analysis should minimize identifiers. Access controls, retention/deletion periods, and any use of interaction text in evaluation require agreement with David and the team. Raw feedback and customer conversations do not belong in the public repository.

Exit states: feedback recorded; proposal awaiting review; proposal rejected; evaluated version released; or prior version restored.

## 9. Quotas, queues, and the 10,000-customer workload

The design must separate connected customers from active inquiry rate.

For capacity planning:

- Inquiry arrival rate depends on concurrent customers and assumed inquiries per customer per unit time.
- Model-call rate depends on arrival rate and the fraction admitted to generation.
- Approximate in-flight model calls equal model-call rate multiplied by mean model-call duration under stable conditions.

Vlad and David own the shared workload assumptions and calculations. This section supplies the AI-boundary controls:

- Apply per-customer/tenant limits and an aggregate generation concurrency limit.
- Use bounded queues and queue-wait deadlines; include waiting time in the end-to-end deadline.
- When capacity is exhausted, return a controlled busy response and retry guidance rather than accepting unlimited work.
- Apply an agreed circuit-breaker policy during sustained provider failures.
- Keep escalation persistence and authorized status review available independently of model generation, with their own capacity limits.
- Prevent one customer or tenant from consuming the entire generation budget.
- Avoid immediate mass retries after an outage.
- If caching is introduced, key entries by authorized scope, source/configuration versions, and relevant context; invalidate on access or source changes.
- Track queue depth, rejection rate, model latency, quota errors, timeout rate, escalation save failures, and oldest queued human request.

Provider selection must consider sustainable request/token quotas, permitted data handling, context limits, latency, and cost. Free evaluation access does not establish suitability for the production workload.

Numerical limits and service objectives remain proposals until measured or justified and recorded in the team decision log. No 10,000-customer capacity claim is made.

## 10. Verification scenarios

These are planned checks, not completed test results.

| Scenario | Expected outcome | Contracts |
|---|---|---|
| Permitted question with supporting passages | Answer supported by permitted evidence and resolvable citations | C1–C3 |
| Unknown, inaccessible, or removed source | Candidate suppressed or controlled source failure; no restricted content exposed | C1–C3 |
| Insufficient/conflicting evidence | Limitation or clarification and escalation option | C1–C4 |
| Customer requests a human | Reviewed submission and durable acknowledgment | C4–C5 |
| Provider timeout/quota/outage | Preserved question, controlled message, no unsupported answer | C1, C3–C4 |
| Save fails | No success acknowledgment; content retained for retry | C4 |
| Save commits but response is lost | Same-ID retry returns the original request | C4 |
| Concurrent duplicate submissions | Exactly one durable request for the submission ID | C4 |
| Same ID with changed content | Explicit conflict rather than silent duplication | C4 |
| Unauthorized agent access or conflicting claim | Access denied or version conflict | C5 |
| Malicious instructions in source text | No policy override or unauthorized action | C2–C3 |
| Feedback proposes a harmful change | Human review/evaluation prevents release | C6 |
| Queue/provider capacity is exhausted | Bounded admission and controlled overload behavior | C1, C3 |
| Required customer-data dependency fails | Controlled failure; no fabricated customer context | C7 |

Carry forward the agreed fictional evaluation set from B02 and source/fallback checks from B07/B10/B11/B12. Production-scale validation requires a separate workload-based plan; prototype results cannot establish it.

## 11. Design rationale contribution

Separating retrieval, generation, escalation, and feedback gives each component a focused responsibility. The inquiry coordinator depends on shared contracts rather than provider-specific response formats. The customer-data adapter enforces permitted access independently of the model.

The main tradeoff is retaining one selected provider behind a replaceable adapter while deferring automatic failover. This reduces integration and verification effort but accepts temporary loss of AI answers during provider failure. Independent escalation preserves a useful recovery path without treating the model as the source of truth.

Reviewed improvements introduce more delay than automatic adaptation, but preserve traceability, evaluation, and rollback. This is appropriate where customer feedback may contain errors, sensitive information, or malicious instructions.

This section contributes to the team's combined 500-word rationale; it is not a replacement for that deliverable or its required architecture citation.

## 12. Open decisions and review requests

- Hanlin: align component names, C1–C7 field names, endpoint/method definitions, error codes, status lookup, ownership/version checks, and agent transitions.
- Vlad: align logical components, queue/storage boundaries, deployment design, and customer-database integration.
- David: review permitted data, logging/retention, evidence-validation limitations, failure scenarios, and workload verification.
- Team: agree on provider selection, evidence acceptance rules, deadlines, queue sizes, retry budget, retention periods, and release/rollback criteria.

Review privacy work in issue #8 and provider comparisons in issue #5. Link the reviewed conclusions here.

Record approved decisions in decisions.md and actual authored/reviewed work in contributions.md. Keep issue #13 open until its acceptance criteria have been reviewed and completion evidence recorded.
