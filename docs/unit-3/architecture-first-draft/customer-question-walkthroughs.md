# Unit 3 — Customer question walkthroughs

These two walkthroughs turn the component responsibilities into interactions for the architecture diagram. They describe intended behavior, not implemented or tested results. The workload remains 10,000 concurrent customer sessions at about 167 new inquiries per second.

## Backlog boundary

The supported-answer flow follows B04/B07/B08/B09/B10. The fallback and single-save behavior follows B11, including failure handling consolidated from B17. B12 manual evaluation remains separate from runtime validation and production load testing. B13 adds saved feedback and review by explicitly authorized staff later in the full backlog; administrator status alone does not grant support access. B13 remains outside the B01–B12 four-week extract.

Customer-specific authorization, an existing customer-database adapter, and agent assignment/status details are proposed Unit 3 design additions. These walkthroughs do not present them as previously approved implementation commitments.

## Walkthrough A — A question with available supporting sources

Illustrative question: “Where can I find the customer portal setup instructions?” Assume an approved fictional guide exists for the example. This does not assert that the document or evaluation case has already been created.

Expected outcome: the customer sees an answer that passes the executable support policy with working, authorized source references. B12 independently evaluates answer quality; source validity alone does not prove support.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| A1 | M1 Browser interfaces → M2 Application/access control | Submit the knowledge question and requested operation through C1, using the authenticated session cookie and server-associated inquiry/correlation ID. Show pending status. Hanlin aligns the operation selector and size limits. | Empty/oversized input receives validation feedback. Keep editable question text in the current form. |
| A2 | M2 Application/access control | Validate input, session and selected operation; derive trusted C9 role/customer/document scope, assign a correlation ID and apply aggregate admission. Account-status selection follows the separate read-only path below. | Deny unauthorized access. If admission/dependency capacity is unavailable, return a controlled status and preserve the question; do not wait indefinitely. |
| A3 | M2 → M3 Knowledge/retrieval; M3 → M9 storage interfaces as needed | Pass the question and trusted permitted-source scope. Retrieve approved passages with stable document, section and version identifiers. Return the permitted passage set to M2. | If no relevant permitted evidence is available, use Walkthrough B without calling the model to invent an answer. Retrieval failure is reported as unavailability, not as proof that no source exists. |
| A3b | M2 → M5 Answer/source validation — C10 prepare_evidence | Before C3, check the permitted retrieved passages against the reviewed, versioned evidence manifest and bind an immutable EvidenceExpectation to this inquiry. Only a ready expectation permits provider generation. | If evidence is insufficient or the precheck fails, times out or is unavailable, make zero C3/provider calls. Return controlled clarification, a support option or unavailability; do not save a support request automatically. |
| A4 | M2 → M4 AI provider adapter → external AI provider | Only after A3b returns a ready inquiry-bound EvidenceExpectation, send the permitted question and retrieved passages with source IDs. Keep C9 context and database fields inside DeskGuide. Wait at most 12 seconds or the remaining overall budget minus the one-second fallback reserve, whichever is shorter; stop dependency waiting by approximately second 19. | On timeout, quota failure, malformed output or open circuit, follow Walkthrough B without an automatic generation retry or second-provider failover. |
| A5 | External provider → M4 → M2 | Return a structured candidate answer and source identifiers associated with the same inquiry. | A result arriving after timeout/cancellation is obsolete and must not overwrite the current fallback view or create a support request. |
| A6 | M2 → M5 Answer/source validation, with M3 resolving source references | After C3, call C10 validate with the candidate and the same inquiry-bound EvidenceExpectation. Check candidate structure, exact approved-answer wording and every required source/version/access reference. Display the answer only if validation passes; otherwise suppress it and return a controlled outcome. | Reject inaccessible, unknown or unresolvable sources and unsupported claims. If validation fails, times out or cannot run, suppress the candidate and return controlled fallback with a support option; do not save a support request automatically. Reviewed manifest fixtures remain an implementation prerequisite; B12 manual review is separate. |
| A7 | M2 → M1 Browser interfaces | Return the result that passed the agreed runtime validation policy, its authorized source references and the matching inquiry ID. Display citations beside the answer. | A disconnected browser must not cause an unrelated or stale result to replace a newer inquiry. No general conversation-history persistence is assumed. |
| A8 | M1 → M2 → M3 when a source is opened | Recheck access to the selected document/section/version and return the authorized source content. | If access changed or the source cannot be resolved, show a clear unavailable/denied result rather than another customer's content or a silently substituted passage. |

Main diagram path: M1 → M2/C1 → M3/C2 permitted retrieval → M2 → M5/C10 prepare_evidence → [ready only] M2 → M4/C3 provider → M2 → M5/C10 validate → M2/C1 answer display → M1. M3 uses its M9 storage interface where needed. A failed or unavailable precheck means zero C3 calls and controlled fallback without an automatic support save. The return to M2 denotes orchestration, not separate deployment.

Customer-data boundary: this general question needs no lookup. For the separate account-status use case, the customer explicitly selects Check my account status through a C1 request selector; a response-side route field alone does not provide that selection. M2 validates the action and scope, calls M7 for customer_id/account_status and returns fixed text without retrieval or AI generation. No database fields reach the provider. Unavailable data is explained; confirmed support saving remains available using trusted identity.

## Walkthrough B — Unsupported/complex inquiry or AI failure, followed by a support request

Entry conditions: no permitted supporting passages; an explicit request for a person or an agreed complexity-routing rule; invalid citations/output; or retrieval/provider timeout, quota or service failure. Keep “insufficient evidence” distinct from “service unavailable.” Complexity and evidence-sufficiency policies are still proposed design decisions.

Expected outcome: the customer receives a clear limitation and can choose to create one durable support request. A saved-request acknowledgement means storage succeeded; it does not mean an agent accepted or resolved the request.

| Step | Component responsible | Information passed / intended action | Failure or alternate outcome |
| --- | --- | --- | --- |
| B1 | M2 Application/access control → M1 Browser interfaces | Return a safe limitation/unavailability reason and the support-request option. Retain the original question in the current editable form. | Hide credentials, raw provider errors and unnecessary internal details. Keeping text in this form does not promise survival across a page reload. |
| B2 | Customer through M1 | When the support form opens, register an unused server-issued ID bound to the customer and operation. Reply IDs also bind the parent request. The customer reviews/edits the content and explicitly confirms or cancels; registration alone creates no visible support request. | Unused IDs expire 30 minutes from registration. Atomically allow at most three unused, unexpired IDs per customer combined across escalation/reply operations. A fourth registration returns 429 with a pending-limit message; never evict an older ID. Expired IDs do not consume slots. Completed receipts follow request retention instead. |
| B3 | M1 → M2 → M6 Escalation/agent workflow | Submit final confirmed content and the registered ID. Revalidate session, customer/operation/parent scope, content and unused-ID validity. Time the support-save operation from application receipt to durable commit and success-response readiness; registration is measured separately. Server deduplication is mandatory. | Reject expired/unknown IDs or unauthorized input with a controlled response. Preserve editable content. Do not recreate an expired request by silently generating a new ID. |
| B4 | M6 → M9 persistence interface | In one transaction, atomically create the support request and its completed receipt under the unique customer/operation/submission identity. Bind the receipt to the confirmed payload so repeats can return the committed result. | If the transaction is known to have failed without saving, report “not saved.” If its outcome is uncertain, report “confirmation unavailable” and resolve using the same identity; do not assert that no record exists. |
| B5 | M9 → M6 → M2 → M1 | After durable commit, return the saved request ID and acknowledgement. | If commit succeeds but acknowledgement is lost, replaying the same authorized ID/payload returns its completed receipt and existing request. Retain completed receipts for the request lifetime and 30 days after resolution. |
| B6 | M2/M6 on retry | Check the registered ID, authorized customer/operation scope, payload match and completed receipt before deciding whether to create, replay or reject. | Completed same-ID/same-content requests return the existing result; changed content conflicts. Unknown or expired unused IDs are rejected, never recreated. Cross-customer receipt lookup is denied. Only a deliberate new submission gets a fresh server-issued ID. |
| B7 | Agent interface M1 → M2 → M6 → M9 | A permitted human opens the saved-request list/detail. Enforce role and record scope on the server before returning content. | Restrict unauthorized requests. Document-administration rights alone do not grant access to customer conversations or support requests. |
| B8 | Agent interface → M2 → M6 → M9 | Proposed states: queued → assigned → in_review → waiting_for_customer → in_review → resolved. Claim/assignment and transitions use atomic owner/version checks. Only the owner changes assigned work within permitted transitions; unfinished work may be released to queued with a reason. | Resolved is terminal; late replies do not reopen it. Stale concurrent changes conflict. A permitted customer reply to waiting_for_customer returns the request to in_review and retains the assigned agent. Hanlin aligns exact contracts; David verifies claim/reply/resolution races. |

Main diagram path: fallback reason → M2 → M1/customer confirmation → M2 → M6 → M9 durable save → M6/M2 → M1 acknowledgement. The agent later follows M1 → M2 → M6 → M9 for permitted review and updates.

Capacity boundary: AI admission and support-request admission are separately bounded. Provider limits, database capacity and agent throughput constrain service. David will test the proposed load and recovery scenarios; numerical in-flight and support limits require sizing evidence.

## Verification and draft contracts

| Check | Expected design behavior / backlog basis |
| --- | --- |
| Supported question and source click | Stable authorized source IDs resolve; expected supporting passages and answer support are manually evaluated under B07/B12. |
| Missing evidence / explicit human request | No unsupported answer is invented. Failed, timed-out or unavailable evidence checks suppress candidates; the customer chooses whether to submit support. Verify supported, unsupported and check-unavailable outcomes. |
| Timeout, quota failure, service failure and malformed output | Use delivered 200 temporarily_unavailable for controlled provider fallback, 429 for customer limits, 503 SERVICE_BUSY for aggregate overload and 504 DEADLINE_EXCEEDED when the deadline expires and a response remains deliverable. Keep C10 validation outcomes distinct; preserve the original question without raw error/secret disclosure. |
| Invalid or inaccessible citation | Reject invalid sources and unsupported candidates under C10 without bypassing permissions. Preserve the independently reviewed B12 set: 12 supported, four unsupported and four ambiguous questions. Existing gates are 10/12 supported correct and all four unsupported falling back; assess ambiguous cases individually. |
| Confirm, cancel, repeat submit, changed content and lost acknowledgement | Cancel creates no support request. Same-ID/same-payload retries replay the committed result; changed payload conflicts and unknown/expired unused IDs cannot create records. Verify atomic three-ID registration, no eviction, cleanup/commit races, duplicate replies and uncertain saves retaining their original ID. |
| Customer/agent permissions and customer-data access | Deny unauthorized/cross-customer access; synthetic examples only. Agent/customer-data extensions are Unit 3 design work. |
| Provider response arriving late | Correlate inquiry results and suppress obsolete UI updates; never auto-save a support request because a provider returned late. |
| Workload and regression | Before testing, fix and independently review eligibility labels, expected outcomes and source versions. Count otherwise-eligible busy/failure outcomes as misses. Measure the 95%/15-second AI target and separate 95%/two-second durable-save target. Simulate ten-minute 166.67/s, two-minute 333.33/s and separate 10,000-arrival/one-second overload cases. B12 and small live-provider checks do not establish production capacity. |

Contract mapping: C1 inquiry/result and explicit account-status selection; C2 retrieval/sources; C3 generation; C4 registered support submission/receipts; C5 agent workflow/replies; C6 feedback/reviewed improvement; C7 read-only customer lookup; C8 document administration; C9 verified access context; C10 runtime evidence/source validation. Hanlin aligns schemas, errors and measurement boundaries with the diagram and proposed decisions.

## Remaining contract and verification work

- Collins: provide executable evidence rules, provider/model quota/data-policy evidence, production breaker window/counter/reset/write rules, and deadline/outcome confirmation.

- Hanlin: align the proposed session/ID values, combined cap, explicit account-status selector, provisioning/permissions, release authorization and save measurement contracts.

- David: review fixed labels, save denominators, session/ID/ownership races, non-author release, deletion/restoration and shared-breaker recovery. These checks remain planned.

- Vlad: reconcile cross-component findings, proposed deployment and final rationale, then obtain all four reviews of one final version.
