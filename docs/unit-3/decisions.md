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
- Application improvement release authority: Vlad primary, Hanlin accepted backup. David declined the additional role; the technical release policy remains pending final team agreement. The change author cannot provide final release authorization.
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

## November 3 — Evidence and breaker direction selected

Vlad selected Collins's conservative extractive prototype policy, accepting limited FAQ coverage, with an explicit immutable inquiry-bound evidence expectation supplied to C10. Activation requires a reviewed manifest; unavailable checks fail closed. Retain the prototype 3-failures/60-second breaker and provisional production 50-percent/minimum-20/10-second window, 30-second cooldown and single 20-second recovery lease. Completed valid provider responses remain availability successes even when content validation rejects them. Use 503 before admission, controlled 200 unavailable after admission, and 504 at the hard deadline. See the [complete decisions](proposed-decisions.md#7-ai-evidence-support-policy--d03c10) for ownership and remaining evidence. Final combined-version team approval and executed validation remain pending.
