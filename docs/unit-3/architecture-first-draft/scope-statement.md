# Unit 3 — DeskGuide scope statement

## Scope statement

For Unit 3, I am designing DeskGuide as a customer-service platform that supports 10,000 concurrent customer sessions. Customers will ask basic service questions through an AI chatbot and receive answers grounded in approved knowledge documents, with links to the supporting sources. When the available evidence cannot support an answer, the question is too complex, or the AI service fails, DeskGuide will explain the limitation and offer a handoff to a human agent. Customers will review the information shared with the agent, and the system will acknowledge a support request only after it has been saved.

The initial customer-specific operation is an explicitly selected, read-only account-status check through C1/M7. The application reads only customer_id and account_status using trusted session scope and returns a fixed response without retrieval or model generation. Customer, agent and administrator permissions remain separate. Feedback informs bounded source or answering changes through independent review, evaluation, versioned release and rollback.

My architecture draft will show the system’s responsibilities, component boundaries, directional data flows, external connections, and capacity assumptions. I will keep those responsibilities clear enough for junior developers to understand and maintain. Hanlin’s interface contracts, Collins’s AI integration flows, and David’s verification plan will be checked against the same design.

## Behavior the architecture must cover

| Requirement | Scope for this draft | Backlog continuity |
| --- | --- | --- |
| Basic inquiries and supported answers | Retrieve permitted passages; return an answer with resolvable source references | B02, B07, B08, B10 |
| Complex, unsupported, or failed inquiries | Preserve the question; offer a customer-reviewed support request; save once despite retries; acknowledge the durable result; route to an authorized agent | B11, B13; B17 remains consolidated into B11 |
| Existing customer database | Explicit read-only account status: customer_id/account_status, trusted customer scope, no model call; unavailable data is explained without guessing | Production design addition P02; preserve B04/B09 authorization principles |
| Learning from interaction patterns | Review permitted feedback; independently evaluate versioned improvements; require non-author release authorization and a rollback reference | B13/B16 plus production design addition P04 |
| 10,000 concurrent customers | Use the highest previously proposed workload and document the resulting demand | Production design addition P01; preserve B05/B12 measurement requirements |
| Maintainability | Give components focused responsibilities, explicit contracts, and understandable failure behavior | B03, B04, B19 |

## Boundaries for Unit 3

This is a system design specification. The first draft does not include application implementation, a live deployment, actual customer-database access, or measured proof of 10,000-customer capacity. Examples and any later local demonstrations will use fictional documents and synthetic customer data.

Proposed production design: one modular Flask application replicated behind HTTPS ingress, with shared PostgreSQL state. Improvements require independent review, passed evaluation, versioning and non-author release authorization. Automatic second-provider failover remains deferred. Provider capacity, hosting and deployment sizing require evidence.

The original employee-support prototype remains the backlog baseline. This Unit 3 draft extends that baseline to the customer-service requirements without claiming the earlier Flask/SQLite prototype already satisfies production capacity.

## Working dates

Team responses: Tuesday, November 3, 2026, at 10:00 a.m. Eastern; I will consolidate replies afterward. Working submission cutoff: November 3 at 11:59 p.m. Eastern. Unanswered technical items remain open.

## Source basis

- [Unit 3 assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

- [Refined eight-week backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-eight-week-backlog-v2.md)

- [Refined four-week sprint backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-four-week-sprint-backlog.md)

- [Current assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

The source backlog’s prototype estimates remain historical. Additional production-design work must be estimated separately.
