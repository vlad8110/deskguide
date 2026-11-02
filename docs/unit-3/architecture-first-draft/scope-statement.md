# Unit 3 — DeskGuide scope statement

*November 1 shared-source snapshot. Current direction: [November 2 proposed decisions](../proposed-decisions.md).*

Author: Vladimyr Merci. Status: proposed; team approval pending.

## Scope statement

For Unit 3, I am designing DeskGuide as a customer-service platform that supports 10,000 concurrent customer sessions. Customers will ask basic service questions through an AI chatbot and receive answers grounded in approved knowledge documents, with links to the supporting sources. When the available evidence cannot support an answer, the question is too complex, or the AI service fails, DeskGuide will explain the limitation and offer a handoff to a human agent. Customers will review the information shared with the agent, and the system will acknowledge a support request only after it has been saved.

The design will integrate with an existing customer database through an authorized interface that limits access to the information needed for the inquiry. Customer, support-agent, and administrator permissions will be defined separately so customers cannot access other customers’ records or invoke restricted operations. Feedback and recurring interaction patterns will inform improvements through a reviewed process: identify a problem, propose a knowledge or answering change, evaluate it, and release a version that can be rolled back.

My architecture draft will show the system’s responsibilities, component boundaries, directional data flows, external connections, and capacity assumptions. I will keep those responsibilities clear enough for junior developers to understand and maintain. Hanlin’s interface contracts, Collins’s AI integration flows, and David’s verification plan will be checked against the same design.

## Behavior the architecture must cover

| Requirement | Scope for this draft | Backlog continuity |
| --- | --- | --- |
| Basic inquiries and supported answers | Retrieve permitted passages; return an answer with resolvable source references | B02, B07, B08, B10 |
| Complex, unsupported, or failed inquiries | Preserve the question; offer a customer-reviewed support request; save once despite retries; acknowledge the durable result; route to an authorized agent | B11, B13; B17 remains consolidated into B11 |
| Existing customer database | Define the authorized data boundary, minimum fields needed, and behavior when data is unavailable | Production design addition P02; preserve B04/B09 authorization principles |
| Learning from interaction patterns | Review permitted feedback/patterns and evaluate versioned improvements; define access and retention | B13/B16 plus production design addition P04 |
| 10,000 concurrent customers | Use the highest previously proposed workload and document the resulting demand | Production design addition P01; preserve B05/B12 measurement requirements |
| Maintainability | Give components focused responsibilities, explicit contracts, and understandable failure behavior | B03, B04, B19 |

## Boundaries for Unit 3

This is a system design specification. The first draft does not include application implementation, a live deployment, actual customer-database access, or measured proof of 10,000-customer capacity. Examples and any later local demonstrations will use fictional documents and synthetic customer data.

Proposed production design: one modular Flask application replicated behind HTTPS ingress, with shared PostgreSQL state. Improvements require review, evaluation, versioning and an approved release. Automatic second-provider failover remains deferred. Provider capacity, hosting and deployment sizing remain pending.

The original employee-support prototype remains the backlog baseline. This Unit 3 draft extends that baseline to the customer-service requirements without claiming the earlier Flask/SQLite prototype already satisfies production capacity.

## Working dates

Internal combined review: November 1; corrections and agreement: November 2. Working submission deadline: November 3, 2026, at 11:59 p.m. Eastern.

## Source basis

- [Unit 3 assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

- [Refined eight-week backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-eight-week-backlog-v2.md)

- [Refined four-week sprint backlog](https://github.com/vlad8110/deskguide/blob/main/docs/backlog/refined-four-week-sprint-backlog.md)

- [Current assignment requirements](https://github.com/vlad8110/deskguide/blob/main/docs/unit-3/assignment-requirements.md)

The source backlog’s prototype estimates remain historical. Additional production-design work must be estimated separately.
