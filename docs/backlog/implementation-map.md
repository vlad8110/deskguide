# Backlog implementation and design map

## Current status

Reviewed October 29: `app/` and `tests/` have no runnable implementation or test suite. No B-item is marked implemented or tested. The Unit 3 work incorporates backlog requirements into design; that is not completion of the application backlog. Owners must attach code/PR/test evidence before changing status.

## Scope reconciliation

The refined backlog describes a bounded fictional employee-support prototype. Current Unit 3 scope expands the **design** to customer service, 10,000 concurrent customers, existing customer-database integration, a human-agent workflow and reviewed learning feedback. Preserve the earlier acceptance criteria; add production design requirements separately rather than rewriting historical sources.

- B06: SQLite remains in the prototype source; production storage/connection limits and replication strategy require a recorded design choice.
- B09: controlled demo roles remain the prototype baseline; customer/agent permissions and cross-customer isolation must be designed for production.
- B11: retain question preservation, durable single-save IDs, retry handling, controlled errors and early tests; extend to acknowledged agent handoff/state transitions.
- B12: retain sequential demo measurements; they do not establish 10,000-customer capacity. Define a separate workload/capacity validation plan.
- B13: saved feedback is not the entire learning loop; add authorized review, evaluation, versioning and rollback.
- B17: second-provider failover stays deferred and B17 effort stays consolidated into B11.
- B20: the local/recorded demonstration remains the refined baseline. The new production architecture is a design deliverable, not a promise of public hosting or measured large-scale capacity.

## Traceability

| Item | Source task | Lead | Coordination issue | Design/verification coverage | Status |
| --- | --- | --- | --- | --- | --- |
| [B01](refined-eight-week-backlog-v2.md#b01) | Agree on core stories, exclusions, and the backlog. | Vlad | [#11](https://github.com/vlad8110/deskguide/issues/11) | R1–R6; scope/requirements | Planned; implementation/test evidence absent |
| [B02](refined-eight-week-backlog-v2.md#b02) | Prepare a bounded fictional document collection and evaluation cases. | Collins + David | [#13](https://github.com/vlad8110/deskguide/issues/13) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Retrieval corpus/evaluation; R1 | Planned; implementation/test evidence absent |
| [B03](refined-eight-week-backlog-v2.md#b03) | Sketch employee and administrator workflows and component boundaries. | Hanlin + Vlad | [#12](https://github.com/vlad8110/deskguide/issues/12) / [#11](https://github.com/vlad8110/deskguide/issues/11) | Component and UI boundaries; R1/R2/R6 | Planned; implementation/test evidence absent |
| [B04](refined-eight-week-backlog-v2.md#b04) | Define request/response contracts and error cases. | Hanlin | [#12](https://github.com/vlad8110/deskguide/issues/12) | C1–C7 contracts; R1–R6 | Planned; implementation/test evidence absent |
| [B05](refined-eight-week-backlog-v2.md#b05) | Compare two free model API options. | Collins + David | [#5](https://github.com/vlad8110/deskguide/issues/5) / [#13](https://github.com/vlad8110/deskguide/issues/13) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Provider adapter/capacity assumptions; R1/R4 | Planned; implementation/test evidence absent |
| [B06](refined-eight-week-backlog-v2.md#b06) | Create the Flask skeleton and SQLite schema. | Vlad | [#11](https://github.com/vlad8110/deskguide/issues/11) | Application/persistence; production storage review | Planned; implementation/test evidence absent |
| [B07](refined-eight-week-backlog-v2.md#b07) | Implement passage retrieval from fictional documents. | Collins | [#13](https://github.com/vlad8110/deskguide/issues/13) | Retrieval/source access; C2 | Planned; implementation/test evidence absent |
| [B08](refined-eight-week-backlog-v2.md#b08) | Build the employee question and result views. | Hanlin | [#12](https://github.com/vlad8110/deskguide/issues/12) | Question/result states; C1 | Planned; implementation/test evidence absent |
| [B09](refined-eight-week-backlog-v2.md#b09) | Implement demo sign-in and employee/administrator authorization. | Vlad + David | [#11](https://github.com/vlad8110/deskguide/issues/11) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Authorization/customer isolation; all contracts | Planned; implementation/test evidence absent |
| [B10](refined-eight-week-backlog-v2.md#b10) | AI user story: As an employee, I want an answer based on relevant fictional documents with source links so I can verify the guidance. | Collins | [#13](https://github.com/vlad8110/deskguide/issues/13) | AI vertical slice; C1/C2/C3 | Planned; implementation/test evidence absent |
| [B11](refined-eight-week-backlog-v2.md#b11) | Offer the support-request fallback and handle failures from the selected AI provider. | Hanlin + Collins; David tests | [#12](https://github.com/vlad8110/deskguide/issues/12) / [#13](https://github.com/vlad8110/deskguide/issues/13) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Escalation/failure/idempotency; C3/C4/C5 | Planned; implementation/test evidence absent |
| [B12](refined-eight-week-backlog-v2.md#b12) | Evaluate initial answer support and response time. | David | [#14](https://github.com/vlad8110/deskguide/issues/14) | Answer/citation/latency evidence; R1/R4 | Planned; implementation/test evidence absent |
| [B13](refined-eight-week-backlog-v2.md#b13) | Add feedback and administrator request review. | Hanlin + Vlad | [#12](https://github.com/vlad8110/deskguide/issues/12) / [#11](https://github.com/vlad8110/deskguide/issues/11) | Feedback/agent review; C5/C6 | Planned; implementation/test evidence absent |
| [B14](refined-eight-week-backlog-v2.md#b14) | Add administrator management of the bounded document collection. | Hanlin + Collins | [#12](https://github.com/vlad8110/deskguide/issues/12) / [#13](https://github.com/vlad8110/deskguide/issues/13) | Document management/source stability; C2 | Planned; implementation/test evidence absent |
| [B15](refined-eight-week-backlog-v2.md#b15) | Package the alpha and conduct peer review. | David + team | [#14](https://github.com/vlad8110/deskguide/issues/14) | Alpha package and peer review | Planned; implementation/test evidence absent |
| [B16](refined-eight-week-backlog-v2.md#b16) | Test authorization and hostile document instructions and recheck provider-failure handling. | David + Collins | [#14](https://github.com/vlad8110/deskguide/issues/14) / [#8](https://github.com/vlad8110/deskguide/issues/8) | Security and regression | Planned; implementation/test evidence absent |
| [B17](refined-eight-week-backlog-v2.md#b17) | Handle failures from the selected AI provider through a consistent error response and support-request fallback. | Collins + David | [#13](https://github.com/vlad8110/deskguide/issues/13) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Consolidated into B11; no duplicate effort | Consolidated into B11; not separately implemented |
| [B18](refined-eight-week-backlog-v2.md#b18) | Prioritize and resolve the most consequential alpha defects. | Vlad + team | [#11](https://github.com/vlad8110/deskguide/issues/11) | Defect prioritization | Planned; implementation/test evidence absent |
| [B19](refined-eight-week-backlog-v2.md#b19) | Prepare the user guide, architecture notes, and demonstration script. | Hanlin + Vlad | [#12](https://github.com/vlad8110/deskguide/issues/12) / [#11](https://github.com/vlad8110/deskguide/issues/11) | User and architecture documentation | Planned; implementation/test evidence absent |
| [B20](refined-eight-week-backlog-v2.md#b20) | Demonstrate DeskGuide from a clean local setup and provide a recorded walkthrough. | Vlad + David | [#11](https://github.com/vlad8110/deskguide/issues/11) / [#14](https://github.com/vlad8110/deskguide/issues/14) | Clean local demonstration; not production capacity proof | Planned; implementation/test evidence absent |
| [B21](refined-eight-week-backlog-v2.md#b21) | Rehearse with fictional employee questions. | David + team | [#14](https://github.com/vlad8110/deskguide/issues/14) | Scenario rehearsal | Planned; implementation/test evidence absent |
| [B22](refined-eight-week-backlog-v2.md#b22) | Run final regression and clean-setup validation. | David | [#14](https://github.com/vlad8110/deskguide/issues/14) | Regression and clean setup | Planned; implementation/test evidence absent |
| [B23](refined-eight-week-backlog-v2.md#b23) | Assemble the final project portfolio and stakeholder presentation. | Vlad + team | [#11](https://github.com/vlad8110/deskguide/issues/11) | Portfolio and stakeholder presentation | Planned; implementation/test evidence absent |
| [B24](refined-eight-week-backlog-v2.md#b24) | Obtain final agreement and submit the required deliverables. | Vlad + team | [#11](https://github.com/vlad8110/deskguide/issues/11) | Agreement and submission evidence | Planned; implementation/test evidence absent |

## Production design additions — review required

| ID | Addition | Lead | Evidence needed |
| --- | --- | --- | --- |
| P01 | 10,000-customer workload, capacity and overload design | Vlad + David | Assumptions/calculations, architecture, bounded queue/quota policy and load-validation plan |
| P02 | Existing customer database adapter and scoped authorization | Vlad + Hanlin | Typed contract, minimum fields, failure semantics and isolation checks |
| P03 | Explicit human-agent escalation workflow | Collins + Hanlin | State/sequence diagram, consent, acknowledgement, durable retry and authorized agent actions |
| P04 | Reviewed learning/improvement feedback loop | Collins + David | Governance, retention, evaluation, versioning and rollback |

These additions are new design work and are not silently included in the old 51–74-hour estimate. Confirm capacity and implementation scope before committing dates or claiming delivery.

## Completion gate

Each item needs linked implementation, acceptance checks with actual results, peer review and residual limitations. Documentation-only items need the actual reviewed artifact. Record owner-confirmed progress rather than checking historical tasks complete based on their age. Current assignment dates remain in the Unit 3 delivery schedule.
