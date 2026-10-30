# Week 3 delivery schedule

All times are **Eastern**. Our working submission deadline is **Tuesday, November 3, 2026, at 11:59 p.m.** Internal milestones below organize the team’s work; report conflicts in your assigned issue promptly.

| When | Deliverable and action | Lead / contributors | Where to deliver |
| --- | --- | --- | --- |
| Friday, October 30 | Confirm responsibilities, availability, blockers, component boundaries and assumptions for 10,000 concurrent customers | Everyone; Vlad coordinates | [Kickoff #10](https://github.com/vlad8110/deskguide/issues/10) and each assigned issue |
| Saturday, October 31, by 6 p.m. | First architecture diagram with editable source, labeled boundaries/data flows and capacity assumptions | Vlad; David supports capacity review | [Architecture](architecture.md), PR linked to [#11](https://github.com/vlad8110/deskguide/issues/11) |
| Saturday, October 31, by 6 p.m. | First API/component contracts with typed fields, examples, validation, authorization and errors | Hanlin | [Interface contracts](interface-contracts.md), PR linked to [#12](https://github.com/vlad8110/deskguide/issues/12) |
| Saturday, October 31, by 6 p.m. | Normal answering, failure, human escalation and reviewed-feedback flows | Collins | [AI integration](ai-integration.md), PR linked to [#13](https://github.com/vlad8110/deskguide/issues/13) |
| Saturday, October 31, by 6 p.m. | Requirements coverage, security/failure review and proposed capacity-validation plan | David | [Verification plan](verification-plan.md), PR linked to [#14](https://github.com/vlad8110/deskguide/issues/14) |
| Sunday, November 1 | Combine sections and cross-review: David reviews architecture, Collins reviews interfaces, Hanlin reviews AI flows; resolve inconsistencies and draft rationale | Everyone; Vlad combines | Relevant PR comments and [design rationale](design-rationale.md) |
| Monday, November 2 | Resolve review findings; finish the 500-word rationale and authoritative citation; check diagrams/contracts; record approval of the exact final version | Everyone; Vlad coordinates | PRs, [decisions](decisions.md) and [contributions/approvals](contributions.md) |
| Tuesday, November 3, before 11:59 p.m. | Verify the final export, required submission procedure and final file; complete required LEO submission(s) and record confirmation | Vlad coordinates; each member meets individual submission obligations | Final export in this directory; confirmation linked from assigned issue |

## How to deliver your section

1. Start a focused branch from current main and update the linked Markdown section. Keep editable diagrams and final exports in GitHub too.
2. Open a pull request linked to your assigned issue. State what is ready and what remains open.
3. Request the designated peer review and resolve comments. Post blockers in the issue as soon as they arise.
4. Record actual contributions and review evidence. Final approval must identify the exact reviewed commit and export.

Vlad remains coordinator. Any temporary handoff will be announced explicitly in GitHub. These are design deliverables; do not claim 10,000-customer capacity has been tested.

[Unit 3 hub](README.md) · [Requirements](assignment-requirements.md) · [Ownership and workflow](work-plan.md)
