# Unit 3 architecture review

Author: Vladimyr Merci. November 2 diagram revision; November 1 written-source snapshots. Current review direction: [November 2 proposed decisions](../proposed-decisions.md). Written-source alignment and final approval pending.

Read the [complete architecture review document](architecture-review.md), the [Design Decisions and Review Log](../design-decisions-and-review-log.md), and the [rationale draft](../design-rationale.md).

## Written sections

| Material | Document |
| --- | --- |
| Scope and backlog boundaries | [Scope statement](scope-statement.md) |
| Workload, service target and open sizing decisions | [Workload assumptions](workload-assumptions.md) |
| M1–M9 and C1–C10 responsibilities | [Component responsibilities](component-responsibilities.md) |
| Supported answers and durable human handoff | [Customer question walkthroughs](customer-question-walkthroughs.md) |
| Remaining decisions, owners and dates | [Team review](review-notes.md) |

## Diagrams

The [editable draw.io source](deskguide-unit-3-architecture.drawio) contains two pages: **Component architecture** and **Production deployment**, revised November 2 to reflect the current proposals.

### Component architecture

![DeskGuide component architecture](deskguide-unit-3-architecture.png)

### Proposed production deployment

![DeskGuide proposed production deployment](deskguide-unit-3-production-deployment.png)

M1–M9 are logical modules. The production proposal replicates one modular Flask application behind HTTPS ingress/load balancing with shared PostgreSQL state. The workload assumption is 10,000 active customer sessions averaging one inquiry per minute, approximately 167 inquiries per second. Capacity remains untested.

The diagrams include explicit account-status routing, proposed session/ID limits, non-author release authorization with David as backup, fail-closed evidence checking, and shared admission, breaker and retention policies. Provider/model capacity, resource sizing, executable evidence-support rules and exact breaker update behavior remain assigned for review. See the [review log](../design-decisions-and-review-log.md) for owners and evidence requests.

## Shared editing sources

- [Architecture Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit)
- [Shared draw.io diagram](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO)
- [Same diagram in Google Drive](https://drive.google.com/file/d/1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO/view)

The shared files remain the editable architecture sources. Diagram copies reflect the November 2 revision; written copies still reflect the November 1 Google Doc. Follow the [Week 3 schedule](../week-3-delivery-schedule.md) for team agreement and submission.
