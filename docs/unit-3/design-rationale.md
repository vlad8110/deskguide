# Design rationale — draft for team review

Coordinator: Vladimyr Merci. Revision 1, October 31, 2026.

Working draft based on the [Design Decisions and Review Log](design-decisions-and-review-log.md).

## Rationale body

I propose a modular architecture for DeskGuide that separates customer interaction, application coordination, retrieval, AI generation, evidence validation, human support, customer data, feedback, and persistence. Each module has a focused responsibility. Retrieval owns approved knowledge and source versions; support owns request ownership and state changes. This cohesion helps junior developers understand individual features without learning every implementation detail.

Typed contracts reduce coupling by specifying inputs, outputs, permissions, limits, and failure outcomes. The application coordinates requests through these contracts instead of editing another module's tables or interpreting provider responses directly. Parnas (1972) explains how decomposition supports flexibility and comprehensibility. I apply that principle by hiding provider and storage details behind adapters. These implementations can change while callers retain a stable interface.

The principal tradeoff is choosing one modular application instead of independently deployed microservices. One codebase reduces deployment, troubleshooting, and coordination work for our four-person team. Microsoft (n.d.) describes how a single application can retain internal layers while being replicated for scale. Separate services could support independent releases and scaling, but would add network failures and operational responsibilities. Our proposal accepts scaling the application together initially, while preserving boundaries that could support later separation.

For production design, application instances would sit behind HTTPS ingress and a load balancer, using a production WSGI server. Shared PostgreSQL storage would hold durable support records, permitted feedback, and server-side sessions. SQLite remains appropriate for our local prototype. This deployment proposal does not establish production capacity; resource sizing, database constraints, hosting costs, and provider allowances still require evidence.

Authentication and authorization remain deterministic application responsibilities. I propose secure cookie sessions with CSRF protection and server-side scope checks. Customers access their own records; agents access authorized support work. A read-only adapter limits customer-database access to necessary fields. General knowledge questions avoid customer lookups, while account-status responses use an authorized deterministic template rather than sending database fields to AI.

The AI adapter receives permitted passages and returns a candidate, never authority to change accounts or save requests. Evidence validation checks source identity, version, access, and response structure. Valid citations alone do not prove semantic support, so Collins's runtime evidence policy and manual evaluation remain necessary. Insufficient evidence, provider failure, or admission overload produces an honest limitation and a support option. Generation has bounded deadlines and no automatic retry initially.

Customers confirm support content before submission. Shared transactions and stable submission identities prevent duplicate requests, and acknowledgement follows durable saving. Five explicit states govern agent ownership and customer replies. Feedback links to inquiries even when generation fails. Improvements require independent review, evaluation, versioning, release approval, and a rollback reference, rather than automatic retraining.

Our planning assumption is 10,000 active customers averaging one inquiry per minute, approximately 167 inquiries per second. Free API access cannot demonstrate that capacity. David's staged validation plan separates mocked application load from limited live-provider checks. We will distinguish proposed targets, inspected design evidence, and executed results before claiming readiness. Every test record will identify the environment, configuration, workload, observed results, and any limitations affecting interpretation.

## References

Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. *Communications of the ACM, 15*(12), 1053–1058. https://doi.org/10.1145/361598.361623

Microsoft. (n.d.). *Common web application architectures*. https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures
