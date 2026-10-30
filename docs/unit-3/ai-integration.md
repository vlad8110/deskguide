# AI integration and data flow — working specification

Lead: Collins. Reviewers: Hanlin and David. Vlad checks architecture consistency.
Status: required flows identified; provider and detailed design remain open.

## Flows to specify

1. Supported inquiry: authorize scope → retrieve permitted passages → generate through adapter → validate output/source identifiers → return answer and working citations.
2. Unsupported/complex inquiry: explicit limitation → customer reviews/edits escalation content → confirmed handoff → durable acknowledgement → authorized agent review.
3. Provider timeout, quota or service failure: bounded request → controlled response → preserve question in customer view → offer escalation; never substitute an unsupported answer.
4. Escalation failure/retry: distinguish failed saving from saved-but-response-lost; use stable submission ID to prevent duplicate requests and report recoverable state accurately.
5. Reviewed learning loop: collect permitted feedback/patterns → authorized human review → proposed knowledge/retrieval/prompt change → evaluate against baseline → versioned release or rejection/rollback.

For each flow, identify components, direction, contract IDs, data fields, authorization, storage/logging, failure branches and exit states. Include sequence diagrams where they clarify behavior.

## Integration decisions

- [ ] Document provider-neutral adapter and permitted data boundary; do not select or activate a paid service here.
- [ ] Explain source validation and insufficient-evidence decisions, including limitations.
- [ ] Separate customer-database access from model access; permit only necessary authorized fields.
- [ ] Define human agent queue/state and customer acknowledgement with Hanlin.
- [ ] Define feedback governance, retention and evaluation; automatic model retraining is not assumed.
- [ ] Address quotas, bounded queues, timeouts and overload at the workload Vlad and David define.
- [ ] Cross-check privacy considerations already recorded in issue #8.

Record provider comparisons in existing issue #5 and link conclusions here. No provider access, capacity or answer-quality result is claimed.
