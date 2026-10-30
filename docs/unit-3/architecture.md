# Architecture — working design

Lead: Vlad. Reviewer: David; Hanlin and Collins validate interfaces and AI boundaries.
Status: [first architecture draft available for team review](architecture-first-draft/README.md), not an approved or tested implementation. The shared Google Doc and draw.io file are the editable review sources; this repository includes their Markdown, diagram and PNG snapshots.

## Component inventory

| Component | Responsibility | Boundary to specify |
| --- | --- | --- |
| M1 Browser interfaces | Customer inquiry/citation display; authorized agent and administrator work | Public API and server-side role enforcement |
| M2 Application/access control | Validation, authorization, admission and orchestration | Trusted access scope and component contracts |
| M3 Knowledge/retrieval | Retrieve permitted passages with resolvable source IDs | Ingestion, approved versions, retrieval and source access |
| M4 AI adapter | Provider-neutral generation with bounded failure handling | Permitted input, output, deadlines and quota behavior |
| M5 Answer/source checks | Validate output structure, source IDs, versions and access | Structural checks; manual B12 answer-quality evaluation remains separate |
| M6 Escalation/agent workflow | Save/acknowledge one confirmed handoff and expose authorized agent work | Safe retries, ownership and state changes |
| M7 Customer-data adapter | Authorized minimum data from the existing database | Scoped fields, permitted operations and availability |
| M8 Feedback/improvement | Review interaction patterns and evaluate controlled changes | Retention, access, versioned releases and rollback |
| M9 Persistence interfaces | Durable component-owned support, knowledge and permitted feedback storage | Transactions, identifiers and retention |

See the [detailed responsibilities](architecture-first-draft/component-responsibilities.md) and [customer walkthroughs](architecture-first-draft/customer-question-walkthroughs.md). These are nine logical responsibilities, not nine servers or an automatic commitment to nine separately deployed services.

## Diagram work

- [x] Create an editable component diagram and readable [PNG preview](architecture-first-draft/deskguide-unit-3-architecture.png).
- [x] Label the application boundary and external AI/database services in the first draft.
- [ ] Trace normal answering, uncertain/unsupported answering, provider failure, escalation and feedback.
- [ ] Give each interaction a matching contract ID from interface-contracts.md.
- [x] Add a legend and distinguish logical modules from separately deployed services.

## 10,000-concurrent-customer capacity design

Concurrent customers are not automatically 10,000 simultaneous model requests. Define active sessions, request frequency, peak arrival rate, response time, and simultaneous in-flight work before sizing. Show the calculation and sensitivity to assumptions.

Selected assumption: 10,000 concurrent customer sessions, each generating one inquiry per minute on average, approximately 167 new inquiries per second. The [workload draft](architecture-first-draft/workload-assumptions.md) includes calculations, response-time sensitivity and a separate 10,000-arrival burst scenario. Payloads, service targets, queue bounds, deployment and capacity validation remain open.

- [ ] Define workload mix, payload sizes, sustained and burst rates, latency/error targets and test duration.
- [ ] Decide application replication, session/state strategy and storage design.
- [ ] Address AI provider quotas, queue bounds, backpressure, rate limits and controlled overload behavior.
- [ ] Address connection limits, retrieval/index capacity, database contention and external dependencies.
- [ ] Document recovery, observability and maintenance implications for junior developers.
- [ ] Compare the bounded Flask/SQLite prototype with proposed production choices; justify changes.

Use verification-plan.md for planned load validation. No capacity result has been measured.

## Backlog traceability and first decisions

The [first architecture session](architect-first-session.md) records the earlier workload alternatives. Preserve B03 component boundaries, B04 contracts, B06 storage, B07 source resolution, B09 authorization and B11 duplicate-safe escalation/provider failures. Carry B13 feedback and B14 document/source versioning into the production design without treating them as first-four-week commitments. [The integration map](../backlog/implementation-map.md) separates the prototype criteria from P01–P04 production additions. The selected workload is now a documented assumption; it still needs team review and capacity evidence.
