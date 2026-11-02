# Unit 3 — Customer question walkthroughs

*November 1 shared-source snapshot. Current direction: [November 2 proposed decisions](../proposed-decisions.md).*

Author: Vladimyr Merci. Status: proposed; team approval pending.

These two walkthroughs turn the component responsibilities into interactions for the architecture diagram. They describe intended behavior, not implemented or tested results. The workload remains 10,000 concurrent customer sessions at about 167 new inquiries per second.

## Backlog boundary

The supported-answer flow follows B04/B07/B08/B09/B10. The fallback and single-save behavior follows B11, including the failure handling consolidated from B17. B12's manual evaluation of answer support and response time remains a separate verification activity. B13 adds saved feedback and restricted administrator request review later in the full backlog; it is outside the B01–B12 four-week extract.

Customer-specific authorization, an existing customer-database adapter, and agent assignment/status details are proposed Unit 3 design additions. These walkthroughs do not present them as previously approved implementation commitments.

## Walkthrough A — A question with available supporting sources

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

## Walkthrough B — Unsupported/complex inquiry or AI failure, followed by a support request

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

## Verification and draft contracts

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

## Items to settle before the architecture diagram is finalized

- Collins: define runtime evidence-support and complexity routing, provider/model quotas and breaker counter/reset/write policy.

- Hanlin: specify session expiry/logout/provisioning, registered-ID validity and receipt/ownership concurrency contracts.

- David: provide reproducible service-level/load, expired-ID/duplicate, session/ownership and multi-replica breaker verification.

- Vlad: reconcile cross-component findings, proposed deployment and final rationale, then obtain all four reviews of one final version.
