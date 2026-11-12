# Architecture — working design

Lead: Vlad. Reviewer: David; Hanlin and Collins validate interfaces and AI boundaries.

Status: [November 2 proposed decisions](proposed-decisions.md) available for team review; responses due **November 3, 2026, at 10:00 a.m. Eastern**. Read the [review log](design-decisions-and-review-log.md). The [architecture review hub](architecture-first-draft/README.md) contains the November 2 written draft and corrected diagrams; final contract/team alignment remains pending.

## Component inventory

| Component | Responsibility | Contract or boundary |
| --- | --- | --- |
| M1 Browser interfaces | Customer inquiries, source display, agent and administrator actions | C1/C2b/C4/C5/C6/C8/C9; server-side authorization |
| M2 Application/access control | Validation, permissions, bounded admission and orchestration | C9 verified access context; cookie sessions and CSRF |
| M3 Knowledge/retrieval | Approved source versions, retrieval and document administration | C2 retrieval/sources; C8 administration |
| M4 AI adapter | Permitted model input, bounded generation and shared breaker | C3 generation; separate prototype/production breaker proposals; no internal access context or customer-database fields sent to the provider |
| M5 Evidence/source validation | Pre-generation evidence readiness and inquiry-bound expectation; post-generation candidate, source/version/access and exact approved-answer checks | C10 prepare_evidence before C3 and validate before display; B12 manual evaluation remains offline |
| M6 Support/agent workflow | Registered IDs, atomic save/replay, ownership and state transitions | C4/C5; acknowledgement only after durable commit |
| M7 Customer-data adapter | Read-only authorized customer_id/account_status lookup | C7; deterministic account-status response without AI |
| M8 Feedback/improvement | Inquiry-linked feedback, independent review, evaluated releases and rollback | C6; Vlad primary; Hanlin backup; non-author release permission; changes through M3/C8 or M4 |
| M9 Persistence interfaces | Component-owned durable knowledge, support, feedback, sessions and breaker state | Shared PostgreSQL transactions, receipts and leases |

See the [detailed responsibilities](architecture-first-draft/component-responsibilities.md) and [customer walkthroughs](architecture-first-draft/customer-question-walkthroughs.md). These are logical responsibilities, not nine separately deployed services.

## Architecture diagrams

- [Component architecture PNG](architecture-first-draft/deskguide-unit-3-architecture.png)
- [Proposed production deployment PNG](architecture-first-draft/deskguide-unit-3-production-deployment.png)
- [Editable two-page draw.io source](architecture-first-draft/deskguide-unit-3-architecture.drawio)

The component view includes C1–C10 boundaries, registered submission receipts, runtime validation, customer-data isolation and approved improvement routes. The production view shows HTTPS ingress/load balancing, replicated modular Flask applications using production WSGI, shared PostgreSQL state and separate external AI/customer-database dependencies.

## Workload and service proposal

Selected assumption: 10,000 active customer sessions, each generating one inquiry per minute on average, approximately 166.67 new inquiries per second. The worst-case AI planning scenario requires 10,000 model calls per minute. This assumption is separate from the assignment's concurrency requirement.

Proposed service level: at least 95% of all eligible inquiries receive a supported AI answer within 15 seconds. Eligible busy, timeout, invalid-answer and unnecessary-fallback outcomes count as misses. Apply a 20-second end-to-end deadline, with the provider limited to 12 seconds or the remaining budget minus the one-second fallback reserve, whichever is shorter. Use bounded admission without an AI waiting queue and separately bounded support admission.

The [workload document](architecture-first-draft/workload-assumptions.md) details the denominator, calculations, two-minute 2× load and separate 10,000-arrival/one-second burst. Provider capacity, resource sizing, payload/in-flight/support limits and executed load evidence remain pending. No production-capacity result has been measured.

## Remaining review

Respond in your existing issue or section PR by **Tuesday, November 3, 2026, at 10:00 a.m. Eastern**. The [complete proposal](proposed-decisions.md) supplies session/ID defaults, explicit account-status selection, release independence, retention, test labels and measurement rules.

- Hanlin: C1–C10 schemas, session/identity details, submission-ID registration/expiry and ownership/version conflicts.
- Collins: provider/model quota evidence, runtime evidence-support rules and shared-breaker counter/reset/write policy.
- David: denominator-aware service-level tests, expired-ID/duplicate races, session/ownership isolation and breaker recovery across replicas.
- Vlad: reconcile the architecture, contracts and rationale and coordinate all four reviews of one final version.

The shared Google Doc and draw.io file remain the editable architecture sources. Local snapshots reflect the November 2 written source plus Hanlin's accepted backup role and the diagram-connection corrections. The shared files still require these corrections. Final agreement and submission remain pending.

## Backlog traceability

Preserve B03 component boundaries, B04 contracts, B06 storage, B07 source resolution, B09 authorization and B11 durable duplicate-safe escalation. B13 feedback and B14 document versioning remain later full-backlog work. Customer-data integration, detailed agent workflow and governed improvement are Unit 3 design additions. The [implementation map](../backlog/implementation-map.md) distinguishes prototype criteria from P01–P04 production additions. Automatic second-provider failover remains deferred; B17 remains consolidated into B11.
