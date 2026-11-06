# Unit 3 — System Design Specification

**Working deadline: Tuesday, November 3, 2026, 11:59 p.m. Eastern.** This is the cutoff Vlad selected for planning and delivery.

Design DeskGuide as a customer-service platform for **10,000 concurrent customers**. This is a design requirement, not a measured capacity claim. Vlad remains Lead Architect and continuing coordinator; temporary handoffs will be announced explicitly in GitHub.

## Delivery schedule

Follow the [Week 3 delivery schedule](week-3-delivery-schedule.md) for section drafts, peer review, final agreement and Tuesday submission.

## Start here

**Team response cutoff: Tuesday, November 3, 2026, at 10:00 a.m. Eastern.** Review the [complete revised proposed decisions](proposed-decisions.md) and provide remaining feedback/evidence in your existing issue or section PR by then. I will prepare the final revision after the cutoff.

The [Design Decisions and Review Log](design-decisions-and-review-log.md) consolidates D01–D23, the source of each concern, proposed solutions, owners, evidence requests and approval status. Review your assigned items and the [500-word rationale draft](design-rationale.md). Team agreement is pending.

The [November 6 C4 correction request](final-review-request.md) addresses David’s C1 example finding from his November 5 C3 review. See the [pending-review resolution](pending-review-resolution-nov6.md) for addressed findings and outstanding owner decisions, and the [PR #16/#18 reconciliation](review-reconciliation-nov5.md) for integration recommendations. The shared architecture sources retain the November 3 correction; combined-version approval remains pending.

1. Read [requirements](assignment-requirements.md) and [the kickoff](team-kickoff.md).
2. Confirm your assigned issue, availability, and blockers in GitHub.
3. Follow [the work plan](work-plan.md), edit your section on a branch, and open a pull request for review.
4. Record decisions in [the decision log](decisions.md) and actual work in [contributions](contributions.md).

| Document | Lead | Review support |
| --- | --- | --- |
| [Architecture](architecture.md) | Vlad | David; Hanlin and Collins check boundaries |
| [Interface contracts](interface-contracts.md) | Hanlin | Collins and David |
| [AI integration](ai-integration.md) | Collins | Hanlin and David |
| [Design rationale](design-rationale.md) | Vlad assembles; everyone contributes | Whole team |
| [Design Decisions and Review Log](design-decisions-and-review-log.md) | Vlad coordinates; named item owners respond | Whole team |
| [Verification and review](verification-plan.md) | David | Whole team |

GitHub is the coordination hub for assignment files, decisions, task updates and review records. The shared Google Doc and draw.io file remain the editable architecture sources. Repository copies are snapshots. The Flask/SQLite prototype and the production capacity design remain separate.

[Assignment instructions](https://leocontent.umgc.edu/content/umuc/tus/cmsc/cmsc495/2268/unit-3/unit-3-assignment-1-instructions.html?ou=1541050) · [LEO submission and rubric](https://learn.umgc.edu/d2l/le/lessons/1541050/topics/37352126)

## Published coordination

- [Kickoff issue #10](https://github.com/vlad8110/deskguide/issues/10)
- [Vlad: architecture and coordination #11](https://github.com/vlad8110/deskguide/issues/11)
- [Hanlin: interfaces #12](https://github.com/vlad8110/deskguide/issues/12)
- [Collins: AI integration #13](https://github.com/vlad8110/deskguide/issues/13)
- [David: verification #14](https://github.com/vlad8110/deskguide/issues/14)
- [Planning documents review PR #9](https://github.com/vlad8110/deskguide/pull/9)

## Backlog and first architecture session

- [Original and refined backlog hub](../backlog/README.md)
- [Refined four-week sprint](../backlog/refined-four-week-sprint-backlog.md)
- [Backlog implementation/design map](../backlog/implementation-map.md)
- [Vlad’s first architecture session: workload options and components](architect-first-session.md)
