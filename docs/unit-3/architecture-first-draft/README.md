# Unit 3 architecture review

Author: Vladimyr Merci. Updated: November 1, 2026. Status: proposed; team approval pending.

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

The [editable draw.io source](deskguide-unit-3-architecture.drawio) contains two pages: **Component architecture** and **Production deployment**.

### Component architecture

![DeskGuide component architecture](deskguide-unit-3-architecture.png)

### Proposed production deployment

![DeskGuide proposed production deployment](deskguide-unit-3-production-deployment.png)

M1–M9 are logical modules. The production proposal replicates one modular Flask application behind HTTPS ingress/load balancing with shared PostgreSQL state. The workload assumption is 10,000 active customer sessions averaging one inquiry per minute, approximately 167 inquiries per second. Capacity remains untested.

Provider/model capacity, resource sizing, session and unused-ID lifetimes, runtime evidence-support rules, and breaker update details remain assigned for review. See the [review log](../design-decisions-and-review-log.md) for owners and evidence requests.

## Shared editing sources

- [Architecture Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit)
- [Shared draw.io diagram](https://app.diagrams.net/#G1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO)
- [Same diagram in Google Drive](https://drive.google.com/file/d/1E3yDdOnoZSku1W8ejSJnkibDA3NcrGXO/view)

The shared files remain the editable architecture sources; these repository copies reflect the November 1 review draft. Follow the [Week 3 schedule](../week-3-delivery-schedule.md) for team agreement and submission.
