# C1 inquiry coordinator

`POST /v1/inquiries` accepts a customer question using the existing cookie session and `X-CSRF-Token`. Agents and document administrators cannot use this customer route. Customer scope comes from the server session; supplied role/customer fields do not grant access.

```json
{"requested_operation":"ask_question","question":"How do I set up the Campus VPN profile?"}
```

The response uses contract version `0.3.3`: `inquiry_id`, nullable `answer_id`, `status`, `route`, nullable `answer_origin` and `answer`, `sources`, nullable `clarification_prompt`, `escalation_offered`, nullable `suggested_reason`, `configuration_version` and `correlation_id`.

## Service integration

Register an implementation of [InquiryServices](../app/inquiry_types.py) at `app.extensions["inquiry_services"]`. There is no default provider or fictional answer service in the product application. Without configured services, the endpoint returns `temporarily_unavailable` with `service_unavailable`, null answer fields and empty sources.

| Order | Internal method | Responsibility |
| --- | --- | --- |
| 1 | `retrieve(ctx, question, top_k=5, deadline_ms=...)` | Collins: enforce source access and approved-version selection; return permitted passages with their titles. |
| 2 | `prepare_evidence(ctx, inquiry_id, question, retrieved, deadline_ms=...)` | Collins: use the independently reviewed manifest; return ready with an immutable expectation, insufficient evidence, or unavailable checking. |
| 3 | `check_outbound(ctx, question, retrieved, deadline_ms=...)` | Collins/Vlad: approve both the question and every outgoing passage under the configured data policy; deny unknown or restricted content. |
| 4 | `generate(request)` | Collins: accept only question, permitted passage fields, timeout, configuration version and correlation ID. No identity, session or evidence expectation. |
| 5 | `validate(ctx, inquiry_id, candidate, retrieved, expectation, deadline_ms=...)` | Collins: recheck exact source resolution/current permission, active manifest/policy and answer support; return pass with all checked references. |

The coordinator checks expectation ownership, required excerpt ranges and text, cited-reference membership/coverage, and normalized equality to the preselected answer. Preparation must finish before generation. The original expectation is retained for the same inquiry. Missing checks, invalid output and dependency failures suppress the answer. Nothing retries generation or automatically creates support records.

`GenerationPassage` omits source display titles; those are used only to format the returned citation. C2b links include the exact source, section and version. Implementing and verifying that source-view endpoint remains Collins/Hanlin's integration work; the coordinator tests do not establish that those links resolve in the running app.

## Admission, time and storage

SQLite transactions record admission before dependency work, with one active inquiry per customer, five inquiries per rolling minute and a configurable application-wide cap (`INQUIRY_MAX_ACTIVE`, default 5). A second active inquiry returns 429; aggregate saturation returns 503 `SERVICE_BUSY`, both with `Retry-After`. There is no application work queue. These are local prototype inquiry limits, not provider quota/token enforcement or measured production capacity. Abandoned processing markers stop consuming admission after 20 seconds.

Dependencies receive a remaining-time budget: retrieval at most 2 seconds, generation at most 12 seconds, and a one-second fallback reserve inside the 20-second inquiry budget. The coordinator discards returned results that exceed a stage budget; a result beyond the overall deadline yields 504. **Adapters must implement cancellable or bounded I/O using the supplied timeout.** This synchronous coordinator cannot interrupt a dependency that ignores its timeout or protect against an indefinitely blocked call. Do not connect an unbounded adapter. Timeout tests use a controlled clock; they are not live latency measurements.

Only inquiry ID, trusted customer ownership, route, outcome, answer ID, configuration version and creation/expiry times are persisted. No question, answer or passage text is saved or logged. Inquiry metadata expires after 30 days by timestamp. Source-reference persistence and scheduled inquiry/feedback purge are not implemented in this slice. Existing records and schema version 1 are preserved.

## Remaining connections

- Collins: finalize source-grant/version rules, reviewed corpus/manifest, source lookup, C10 validation and outbound policy implementation before connecting a real generation adapter. Account/model/data controls, token/request limits and the shared circuit breaker remain separate provider work.
- Hanlin: connect question/result states and source views, add the agreed notice, and preserve questions on fallback. This backend returns a support offer; the existing browser shell does not yet display it.
- Vlad: connect C7 for explicit `check_account_status`; it currently returns a controlled service-unavailable escalation offer without retrieval/generation. Conversation IDs are rejected unless null because conversation ownership is not implemented. Explicit human-request recognition, clarification prompts, support confirmation/receipts and feedback remain separate workflows.
- David: review the integration types and endpoint cases, independently verify evidence fixtures, and extend tests when actual adapters/source routes arrive. Synthetic tests do not establish live-provider or production capacity.

Run `.venv/bin/python -m pytest -q tests/test_inquiries.py` for the endpoint regressions. Test substitutes exist only in the tests and are never installed by application startup.
