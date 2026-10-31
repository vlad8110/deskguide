# Unit 3 decisions

| Date | Decision | Authority/status |
| --- | --- | --- |
| 2026-10-29 | Use Tuesday, November 3, 11:59 p.m. Eastern as the deadline | Vlad's explicit working cutoff |
| 2026-10-29 | Apply customer-service scenario to DeskGuide; design for 10,000 concurrent customers and existing customer database | Vlad's scope direction; design details require team review |
| 2026-10-29 | Vlad remains coordinator; temporary handoffs announced in GitHub | Replaces prior proposed rotation |
| 2026-10-29 | GitHub is the single place for current assignment files and coordination | Replaces earlier email/Drive coordination proposal |
| 2026-10-29 | Retain existing technical role leads; David leads quality/design verification | Assignments published; member availability/acknowledgement pending |

## Open technical decisions

- Workload definition and performance targets for 10,000 concurrent customers.
- Logical module/deployment boundaries; production storage and customer-data adapter.
- AI provider evaluation, quotas, permitted data and failure behavior.
- Escalation state model, authorization, retention and feedback governance.
- Major architecture tradeoff, supporting source and final design agreement.

Add decisions with alternatives, reasons, author/reviewer and linked issue/PR. Do not mark a pending choice as agreed or tested.

## Backlog migration — October 29

Imported the original and refined Revision 2 backlog text to GitHub. The four-week sprint file is explicitly extracted from Revision 2 B01–B12; no separate final LEO version was verified. Preserve historical wording and integrate production changes through P01–P04 in the implementation map. Workload scenarios in architect-first-session.md are proposals awaiting review. No implementation/test result is inferred.


## Proposed verification decisions — David, October 31 (not yet team-approved)

| Proposal | Reason / alternatives | Owner and approval required | Evidence / status |
| --- | --- | --- | --- |
| **DV01:** Treat 10,000 as simultaneous **connected customer sessions** for preliminary workload calculations, not 10,000 simultaneous model requests | The API rate depends on individual question frequency; model-call rate and provider quotas must be budgeted separately | Vlad + David; Collins checks quotas | [verification plan](verification-plan.md#4-10000-customer-capacity-design-and-future-validation); **proposed, not adopted** |
| **DV02:** Separate R4 production capacity design from the Flask/SQLite local demonstration | A correct bounded local prototype does not demonstrate concurrent storage, session or external AI scaling | Vlad + whole team | [capacity boundary](verification-plan.md#42-architecture-constraints-to-review); **proposed** |
| **DV03:** Require stable customer-scoped idempotency keys and a durable save before acknowledging escalation | Lost acknowledgements and client retries otherwise risk duplicate or false success | Hanlin + Collins; David verifies | [V06–V09](verification-plan.md#3-planned-verification-scenarios--none-executed); **proposed** |
| **DV04:** Approve latency, throughput, failure, recovery and provider-quota targets **before** any capacity test; use mocks and only later bounded provider smoke | Mocked throughput alone cannot demonstrate live external provider capacity | Vlad + Collins + Hanlin + David | [staged validation](verification-plan.md#43-staged-validation--proposal-only-no-large-load-authorized); **proposed; no test authorized** |
| **DV05:** Enforce server-side per-customer authorization and citation source/version checks; minimize outbound AI data | Avoid broken object-level authorization, misleading output, accidental exfiltration | Hanlin + Collins + Vlad; David reviews | [security design](verification-plan.md#2-security-privacy-and-data-integrity-design-checks), [Issue #8](https://github.com/vlad8110/deskguide/issues/8); **proposed** |

These are **review requests**, not changes to Vlad's already-published decisions. Actual acceptance must be recorded by the appropriate lead with a link to the deciding PR/issue comment.
