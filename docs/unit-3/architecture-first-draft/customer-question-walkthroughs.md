# Unit 3 — Customer question walkthroughs

Author: Vladimyr Merci. Working snapshot of the [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit). Make team edits there; refresh this repository copy before publishing a new revision. Team approval is pending.

These two walkthroughs turn the component responsibilities into interactions for the architecture diagram. They describe intended behavior, not implemented or tested results. The workload remains 10,000 concurrent customer sessions at about 167 new inquiries per second.

## Backlog boundary

The supported-answer flow follows B04/B07/B08/B09/B10. The fallback and single-save behavior follows B11, including the failure handling consolidated from B17. B12's manual evaluation of answer support and response time remains a separate verification activity. B13 adds saved feedback and restricted administrator request review later in the full backlog; it is outside the B01–B12 four-week extract.

Customer-specific authorization, an existing customer-database adapter, and agent assignment/status details are proposed Unit 3 design additions. These walkthroughs do not present them as previously approved implementation commitments.

## Walkthrough A — A question with available supporting sources

Illustrative question: “Where can I find the customer portal setup instructions?” Assume an approved fictional guide exists for the example. This does not assert that the document or evaluation case has already been created.

Expected outcome: the customer sees an answer with working, authorized source references. A valid source link is not a guarantee that the answer is factually supported; B12 separately evaluates that quality.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| A1 | M1 Browser interfaces → M2 Application/access control | Submit question, authenticated session information and a client request identifier. Show that the inquiry is pending. Field names and limits remain for Hanlin's contract design. | Empty/oversized input receives validation feedback. Keep editable question text in the current form. |
| A2 | M2 Application/access control | Validate input, establish trusted identity and customer/document scope, and admit work under the configured limits. Associate the inquiry with a correlation ID. | Deny unauthorized access. If admission/dependency capacity is unavailable, return a controlled status and preserve the question; do not wait indefinitely. |
| A3 | M2 → M3 Knowledge/retrieval; M3 → M9 storage interfaces as needed | Pass the question and trusted permitted-source scope. Retrieve approved passages with stable document, section and version identifiers. Return the permitted passage set to M2. | If no relevant permitted evidence is available, use Walkthrough B without calling the model to invent an answer. Retrieval failure is reported as unavailability, not as proof that no source exists. |
| A4 | M2 → M4 AI provider adapter → external AI provider | Send only necessary permitted question/context and retrieved passages, with their identifiers and the inquiry deadline. Keep service credentials server-side. | Provider timeout, quota/service failure or malformed output follows Walkthrough B. Adapter retry limits and any deadline budget need agreement; automatic second-provider failover remains deferred. |
| A5 | External provider → M4 → M2 | Return a structured candidate answer and source identifiers associated with the same inquiry. | A result arriving after timeout/cancellation is obsolete and must not overwrite the current fallback view or create a support request. |
| A6 | M2 → M5 Answer/source validation, with M3 resolving source references | Check output structure, source-ID membership, document/section versions, resolvability and permitted access. Return a displayable candidate or a controlled invalid/unsupported result. | Reject unknown, inaccessible or unresolvable citations. A runtime policy for evidence sufficiency/complexity still requires agreement; structural checks do not prove semantic correctness. |
| A7 | M2 → M1 Browser interfaces | Return the candidate answer, source references and a response associated with the correct inquiry. Display citations beside the answer. | A disconnected browser must not cause an unrelated or stale result to replace a newer inquiry. No general conversation-history persistence is assumed. |
| A8 | M1 → M2 → M3 when a source is opened | Recheck access to the selected document/section/version and return the authorized source content. | If access changed or the source cannot be resolved, show a clear unavailable/denied result rather than another customer's content or a silently substituted passage. |

Main diagram path: M1 → M2 → M3 → M2 → M4/external AI → M2 → M5 → M2 → M1. M3 uses its M9 storage interface where needed. The return to M2 denotes orchestration, not a requirement to deploy every component separately.

Customer-data boundary: this generic question does not require a customer-database lookup. If a permitted inquiry does require customer data, M2 calls M7 using trusted scope; M7 obtains only authorized necessary fields from the existing database and returns a controlled result. The AI has no direct database access. Whether any returned field may be sent to the model must be explicitly defined; database access alone does not authorize external disclosure.

## Walkthrough B — Unsupported/complex inquiry or AI failure, followed by a support request

Entry conditions: no permitted supporting passages; an explicit request for a person or an agreed complexity-routing rule; invalid citations/output; or retrieval/provider timeout, quota or service failure. Keep “insufficient evidence” distinct from “service unavailable.” Complexity and evidence-sufficiency policies are still proposed design decisions.

Expected outcome: the customer receives a clear limitation and can choose to create one durable support request. A saved-request acknowledgement means storage succeeded; it does not mean an agent accepted or resolved the request.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| B1 | M2 Application/access control → M1 Browser interfaces | Return a safe limitation/unavailability reason and the support-request option. Retain the original question in the current editable form. | Hide credentials, raw provider errors and unnecessary internal details. Keeping text in this form does not promise survival across a page reload. |
| B2 | Customer through M1 | Review/edit the content to share, then explicitly submit or cancel. Generate/retain a stable submission ID for this intended submission. | Canceling or viewing the form does not save a human-visible support request. A later separate request receives a new ID. |
| B3 | M1 → M2 → M6 Escalation/agent workflow | Submit confirmed content and stable submission ID. Revalidate content, identity, customer scope and permission before saving. Disable the button while pending for usability; enforce deduplication on the server. | Expired authorization, invalid input or overload gets a controlled response. Preserve editable content and the submission ID for the appropriate retry. |
| B4 | M6 → M9 persistence interface | Atomically save the request under an enforced unique submission identity scoped to the authorized customer. Associate it with the appropriate owner/scope and store only confirmed necessary content. | If the transaction is known to have failed without saving, report “not saved.” If its outcome is uncertain, report “confirmation unavailable” and resolve using the same identity; do not assert that no record exists. |
| B5 | M9 → M6 → M2 → M1 | After durable commit, return the saved request ID and acknowledgement. | If the save commits but the response is lost, retry with the same submission ID returns the existing authorized request for the same payload. It must not insert a second record. |
| B6 | M2/M6 on retry | Check authorized scope and whether the same ID refers to the same confirmed content. | Same ID/same content returns the existing result; same ID/different content returns a conflict. Never expose another customer's record through ID lookup. A deliberate new request receives a new ID. |
| B7 | Agent interface M1 → M2 → M6 → M9 | A permitted human opens the saved-request list/detail. Enforce role and record scope on the server before returning content. | Restrict unauthorized requests. Document-administration rights alone do not grant access to customer conversations or support requests. |
| B8 | Agent interface → M2 → M6 → M9 | Proposed Unit 3 extension: authorize assignment and status updates, save them durably and expose only permitted status information. | Exact states, concurrent-update behavior and who may transition each state need Hanlin/Collins review. No immediate agent availability or resolution time is promised. |

Main diagram path: fallback reason → M2 → M1/customer confirmation → M2 → M6 → M9 durable save → M6/M2 → M1 acknowledgement. The agent later follows M1 → M2 → M6 → M9 for permitted review and updates.

Capacity boundary: both automatic answering and human escalation need capacity policies. Agent work and support-request storage cannot be treated as unlimited. David will review admission, queue limits, waiting-time behavior and recovery against the chosen workload; exact values remain undecided.

## Verification and draft contracts

| Check | Expected design behavior / backlog basis |
| --- | --- |
| Supported question and source click | Stable authorized source IDs resolve; expected supporting passages and answer support are manually evaluated under B07/B12. |
| Missing evidence / explicit human request | No unsupported model answer is invented; routing follows the agreed policy; customer chooses whether to submit support. |
| Timeout, quota failure, service failure and malformed output | Controlled response with original question retained; no secret/raw error disclosure; B11 tests begin during integration. |
| Invalid or inaccessible citation | Reject the structural result; do not bypass source permissions. Semantic answer-quality evaluation remains manual under B12. |
| Confirm, cancel, repeat submit, changed content and lost acknowledgement | Cancel creates no support record; same intended request saves once; changed content under an existing ID conflicts; uncertain outcomes use the same ID to reconcile. These semantics require implementation and test evidence. |
| Customer/agent permissions and customer-data access | Deny unauthorized/cross-customer access; synthetic examples only. Agent/customer-data extensions are Unit 3 design work. |
| Provider response arriving late | Correlate inquiry results and suppress obsolete UI updates; never auto-save a support request because a provider returned late. |
| Workload and regression | B12's sequential demo checks do not establish 10,000-customer capacity; B16 repeats relevant security/failure checks. A separate production-load plan is needed. |

Hanlin will detail C1/C2/C3 for answering, C4/C5 for support and agent review, and C7 for any customer-data lookup. Internal answer-validation and access-context contracts need explicit definitions. C6 covers optional feedback after an interaction; the full reviewed-improvement loop is a separate Unit 3 design flow, not silently completed by these two walkthroughs.

## Items to settle before the architecture diagram is finalized

- Agree on complexity/evidence-sufficiency routing and the limits of runtime checks; preserve manual B12 scoring.

- Agree on allowed customer fields, external-model context, source version handling and retention.

- Define timeout/admission/queue limits, stable retry identity and customer-visible save states.

- Specify agent permissions, assignment/state transitions and change-conflict handling.
