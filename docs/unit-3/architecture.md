# Architecture — working design

Lead: Vlad. Reviewer: David; Hanlin and Collins validate interfaces and AI boundaries.
Status: initial component inventory, not an approved or tested implementation.

## Component inventory to resolve

| Component | Responsibility | Boundary to specify |
| --- | --- | --- |
| Customer browser and agent console | Customer inquiry/citation display; authorized agent work | Public API and role enforcement |
| Application/API | Validation, authorization and orchestration | Business services through stable contracts |
| Retrieval and knowledge store | Retrieve permitted passages with resolvable IDs | Ingestion, retrieval, source access |
| AI adapter | Provider-neutral generation with bounded failure handling | Permitted input, output, deadlines and quota behavior |
| Escalation workflow | Save/acknowledge one handoff and expose agent processing | Safe retries, ownership and state changes |
| Feedback/improvement workflow | Review interaction patterns and evaluate changes | Retention, access, versioned releases and rollback |
| Customer-data adapter | Authorized minimum data from existing database | Read/write permissions, availability, consistency |
| Persistence | Durable request/feedback and metadata storage | Transactions, identifiers and retention |

## Diagram work

- [ ] Create editable UML or equivalent component diagram plus readable rendering under this directory.
- [ ] Label system/trust boundaries and external AI/database services.
- [ ] Trace normal answering, uncertain/unsupported answering, provider failure, escalation and feedback.
- [ ] Give each interaction a matching contract ID from interface-contracts.md.
- [ ] Add a legend and distinguish logical modules from separately deployed services.

## 10,000-concurrent-customer capacity design

Concurrent customers are not automatically 10,000 simultaneous model requests. Define active sessions, request frequency, peak arrival rate, response time, and simultaneous in-flight work before sizing. Show the calculation and sensitivity to assumptions.

- [ ] Define workload mix, payload sizes, sustained and burst rates, latency/error targets and test duration.
- [ ] Decide application replication, session/state strategy and storage design.
- [ ] Address AI provider quotas, queue bounds, backpressure, rate limits and controlled overload behavior.
- [ ] Address connection limits, retrieval/index capacity, database contention and external dependencies.
- [ ] Document recovery, observability and maintenance implications for junior developers.
- [ ] Compare the bounded Flask/SQLite prototype with proposed production choices; justify changes.

Use verification-plan.md for planned load validation. No capacity result has been measured.

## Backlog traceability and first decisions

Start with [Vlad’s first architecture session](architect-first-session.md). Preserve B03 component boundaries, B04 contracts, B06 storage, B07 source resolution, B09 authorization and B11 duplicate-safe escalation/provider failures. Carry B13 feedback and B14 document/source versioning into the production design. [The integration map](../backlog/implementation-map.md) separates the prototype criteria from P01–P04 production additions. Proposed workload figures need review before they become design assumptions.
