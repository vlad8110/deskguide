# Assignment requirements

Working scope selected by Vlad on October 29: apply the customer-service scenario to DeskGuide and design for 10,000 concurrent customers. Work to Tuesday, November 3 at 11:59 p.m. Eastern; do not wait for instructor clarification to begin.

## Required behavior and constraints

| ID | Requirement | Design evidence | Lead |
| --- | --- | --- | --- |
| R1 | Handle basic customer inquiries through an AI chatbot | Normal question, retrieval, evidence check, answer and citations flow | Collins |
| R2 | Escalate complex or unsupported inquiries to human agents | Acknowledged handoff, agent queue/review, failure and retry path | Collins + Hanlin |
| R3 | Learn from interaction patterns | Reviewed feedback/improvement loop, ownership, versioning, evaluation; no assumed automatic retraining | Collins |
| R4 | Serve 10,000 concurrent customers | Workload assumptions, capacity calculation, deployment boundaries, bottlenecks and load-test plan | Vlad + David |
| R5 | Integrate an existing customer database | Adapter, authorized data fields, contracts, ownership and failure behavior | Vlad + Hanlin |
| R6 | Be maintainable by junior developers | Focused modules, stable interfaces, documented setup and test boundaries | All |

## Three deliverables

- Architecture diagram: UML or equivalent notation; all major modules, relationships, component boundaries, interaction points, directional data flow and external connections.
- Interface contracts: API endpoint specifications with request/response formats; component method signatures; typed input/output data; validation and error handling.
- Design rationale: **500 words**, explaining separation of concerns, cohesion/coupling, one major architectural tradeoff, AI integration, and at least one authoritative architecture source.

Submit a professional, technically accurate Design Specification containing all three. Record meaningful contributions from every member. Coding and a deployed service are not separate named deliverables for this assignment.

## Rubric: 160 points

| Criterion | Points | Evidence required |
| --- | --- | --- |
| Component representation and notation | 30 | Precise components, boundaries, relationships and external connections |
| AI integration and data flow | 30 | Distinct chatbot with fully traced answering, human escalation and learning feedback |
| Contracts, validation and errors | 50 | Complete typed fields, constraints, validation, error codes and failure responses |
| Separation of concerns, cohesion and coupling | 50 | Specific examples tied to actual modules and dependencies |

Use [the original instructions](https://leocontent.umgc.edu/content/umuc/tus/cmsc/cmsc495/2268/unit-3/unit-3-assignment-1-instructions.html?ou=1541050) and [rubric](https://learn.umgc.edu/d2l/le/lessons/1541050/topics/37352126). The written Tuesday cutoff is our chosen deadline; the previously displayed November 4, 1:59 a.m. does not extend our plan.

## Scope boundaries

Use fictional/synthetic customers and documents in examples. Describe required customer-database integration without connecting real systems. Review the earlier Flask/SQLite prototype choices against the production requirement; do not present a local demo as proof of capacity. Identify assumptions and unresolved decisions explicitly.
