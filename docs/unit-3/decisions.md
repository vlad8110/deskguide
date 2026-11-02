# Unit 3 decisions

| Date | Decision | Authority/status |
| --- | --- | --- |
| 2026-10-29 | Use Tuesday, November 3, 11:59 p.m. Eastern as the deadline | Vlad's explicit working cutoff |
| 2026-10-29 | Apply customer-service scenario to DeskGuide; design for 10,000 concurrent customers and existing customer database | Vlad's scope direction; design details require team review |
| 2026-10-29 | Vlad remains coordinator; temporary handoffs announced in GitHub | Replaces prior proposed rotation |
| 2026-10-29 | GitHub is the single place for current assignment files and coordination | Replaces earlier email/Drive coordination proposal |
| 2026-10-29 | Retain existing technical role leads; David leads quality/design verification | Assignments published; member availability/acknowledgement pending |
| 2026-10-29 | Select 10,000 concurrent sessions, each submitting one new inquiry per minute on average (approximately 167/second), plus a separately defined synchronized burst scenario | Vlad's workload selection; a design assumption, not measured capacity |
| 2026-10-29 | Use the shared Google Doc and shared draw.io file for editable architecture review; keep links, Markdown/source snapshots and PNG previews in GitHub; reserve PDF for final submission | Vlad's review-format direction; refines the earlier GitHub-only file policy while retaining GitHub coordination |
| 2026-10-29 | Work from the local repository; commit and push only when Vlad explicitly requests the corresponding action | Vlad's local workflow direction; this publication is authorized, later publication requires a new request |

## November 2 review direction

- **Team response cutoff:** Tuesday, November 3, 2026, at 10:00 a.m. Eastern, selected by Vlad; final revision follows the response round.
- [Complete revised proposed decisions](proposed-decisions.md): 14 topics reviewed by Vlad; final team agreement and identified evidence pending.
- Proposed application improvement release authority: Vlad primary, **alternate backup required because David declined the proposed role**; the change author cannot provide final release authorization.
- Shared document/diagram alignment and all four reviews of one final version remain pending.

## Open technical decisions

The [Design Decisions and Review Log](design-decisions-and-review-log.md) supplies proposed resolutions D01–D21, sources, owners, evidence requests and differences from teammate drafts. The [rationale draft](design-rationale.md) reflects those proposals. Team review is pending.

- Payloads, inquiry mix, burst profile and performance targets for the selected workload.
- Logical module/deployment boundaries; production storage and customer-data adapter.
- AI provider evaluation, quotas, permitted data and failure behavior.
- Escalation state model, authorization, retention and feedback governance.
- Major architecture tradeoff, supporting source and final design agreement.

## Backlog migration — October 29

Imported the original and refined Revision 2 backlog text to GitHub. The four-week sprint file is explicitly extracted from Revision 2 B01–B12; no separate final LEO version was verified. Preserve historical wording and integrate production changes through P01–P04 in the implementation map. Workload scenarios in architect-first-session.md are proposals awaiting review. No implementation/test result is inferred.

The later workload selection above supersedes the pending status of the scenario choice. Earlier alternatives remain planning history; the selected assumption is recorded in the [first draft](architecture-first-draft/workload-assumptions.md).

## October 31 proposal publication

Published D01–D21 and the rationale draft for team review. Vlad plans to review PRs #16–#18. Provider/model, capacity evidence, runtime semantic-support policy, authentication/retention details and final agreement remain pending.

## David's November 2 verification response — proposed, pending team adoption

The [November 2 verification alignment document](david-verification-alignment-nov2.md) records David's planned tests N01–N15, session/ID/retention/release rules, pre-labeled 20-question B12 fixture candidate, workload and two-second/15-second denominator definitions against Vlad's 14 proposals. This is a **review response**, not authorization to run tests, adopt policy or publish a release.

**Role decision still required:** Vlad nominated David as backup release authorizer, but David has **declined the nomination**. The requirement for independent non-author release approval and rollback review can be evaluated without assuming David accepted the role.

**Evidence:** [Vlad's PR #18 COMMENTED review](https://github.com/vlad8110/deskguide/pull/18#pullrequestreview-5744463050), [David's architecture COMMENTED review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5730726420), [David's contract COMMENTED review](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5738959296). Final version, peer approval, implementation and capacity outcomes remain open.

## Historical David verification proposals — October 31 (superseded where Vlad's revised direction differs)
 (not yet team-approved)

| Proposal | Reason / alternatives | Owner and approval required | Evidence / status |
| --- | --- | --- | --- |
| **DV01:** Treat 10,000 as simultaneous **connected customer sessions** for preliminary workload calculations, not 10,000 simultaneous model requests | The API rate depends on individual question frequency; model-call rate and provider quotas must be budgeted separately | Vlad + David; Collins checks quotas | [verification plan](verification-plan.md#4-10000-customer-capacity-design-and-future-validation); **proposed, not adopted** |
| **DV02:** Separate R4 production capacity design from the Flask/SQLite local demonstration | A correct bounded local prototype does not demonstrate concurrent storage, session or external AI scaling | Vlad + whole team | [capacity boundary](verification-plan.md#42-architecture-constraints-to-review); **proposed** |
| **DV03:** Require stable customer-scoped idempotency keys and a durable save before acknowledging escalation | Lost acknowledgements and client retries otherwise risk duplicate or false success | Hanlin + Collins; David verifies | [V06–V09](verification-plan.md#3-planned-verification-scenarios--none-executed); **proposed** |
| **DV04:** Approve latency, throughput, failure, recovery and provider-quota targets **before** any capacity test; use mocks and only later bounded provider smoke | Mocked throughput alone cannot demonstrate live external provider capacity | Vlad + Collins + Hanlin + David | [staged validation](verification-plan.md#43-staged-validation--proposal-only-no-large-load-authorized); **proposed; no test authorized** |
| **DV05:** Enforce server-side per-customer authorization and citation source/version checks; minimize outbound AI data | Avoid broken object-level authorization, misleading output, accidental exfiltration | Hanlin + Collins + Vlad; David reviews | [security design](verification-plan.md#2-security-privacy-and-data-integrity-design-checks), [Issue #8](https://github.com/vlad8110/deskguide/issues/8); **proposed** |

These are **review requests**, not changes to Vlad's already-published decisions. Actual acceptance must be recorded by the appropriate lead with a link to the deciding PR/issue comment.
