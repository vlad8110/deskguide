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

## Open technical decisions

- Payloads, inquiry mix, burst profile and performance targets for the selected workload.
- Logical module/deployment boundaries; production storage and customer-data adapter.
- AI provider evaluation, quotas, permitted data and failure behavior.
- Escalation state model, authorization, retention and feedback governance.
- Major architecture tradeoff, supporting source and final design agreement.

Add decisions with alternatives, reasons, author/reviewer and linked issue/PR. Do not mark a pending choice as agreed or tested.

## Backlog migration — October 29

Imported the original and refined Revision 2 backlog text to GitHub. The four-week sprint file is explicitly extracted from Revision 2 B01–B12; no separate final LEO version was verified. Preserve historical wording and integrate production changes through P01–P04 in the implementation map. Workload scenarios in architect-first-session.md are proposals awaiting review. No implementation/test result is inferred.

The later workload selection above supersedes the pending status of the scenario choice. Earlier alternatives remain planning history; the selected assumption is recorded in the [first draft](architecture-first-draft/workload-assumptions.md).
