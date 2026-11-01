# Unit 3 — Component responsibilities

Author: Vladimyr Merci. Status: proposed; team approval pending.

Production proposal: HTTPS ingress/load balancing distributes requests across modular Flask replicas using production WSGI. Shared PostgreSQL holds durable application state through M9. The existing customer database remains a separate read-only dependency. Hosting, replica counts, database sizing and provider capacity remain pending.

## Component proposal

I propose separating DeskGuide into the following logical components. Each component has one main responsibility and communicates through a defined interface. These boundaries will guide the architecture diagram and the team's contracts.

| ID | Component | Main responsibility | Information and interactions | Backlog / contract alignment |
| --- | --- | --- | --- | --- |
| M1 | Browser interfaces | Present customer questions/results, human-agent work, and authorized administration | Sends customer, agent and administrator actions to M2; displays authorized results, source links and controlled failure states. Uses server-issued submission IDs and shows acknowledgement only after durable commit. | B03/B08/B13/B14; C1/C4/C5/C6/C8 |
| M2 | Application and access control | Validate requests, enforce permissions and customer scope, and coordinate use cases | Derives trusted C9 access context from the server-validated session; enforces role, customer and record scope before protected operations. Uses bounded admission, correlation IDs and CSRF checks for state-changing browser requests. | B04/B06/B09; C9 access context across protected C1–C10 operations |
| M3 | Knowledge and retrieval | Manage approved knowledge versions and retrieve only passages the caller may access | Returns approved passages with stable document, section and version identifiers. C8 restricts document administration to authorized administrators. Approved source changes from M8 enter through this boundary. | B02/B07/B14; C2 retrieval; C8 document administration |
| M4 | AI provider adapter | Isolate external generation and provider-specific failure behavior | Sends only the permitted question and retrieved passages to the external provider. Keeps credentials server-side; excludes internal C9 context and customer-database fields. Applies a provider timeout of at most 12 seconds within the 20-second inquiry deadline, with no automatic generation retry. Coordinates shared breaker state through M9. Proposed breaker: three qualifying failures within 60 seconds, then a 30-second cooldown and one global half-open trial protected by a 20-second lease per provider/model/credential scope. Counter/reset and write policy remain with Collins. | B05/B10/B11; C3 |
| M5 | Answer and source validation | Validate candidate structure, authorized citations and evidence under C10 | Checks structure, source membership, document/section versions, access and resolvability. Collins must define the executable runtime evidence-support rule and its limits in C10. Valid citations alone do not prove semantic correctness. B12 manual scoring remains an offline verification activity. | B07/B10 runtime checks; C10 validation; B12 offline manual evaluation |
| M6 | Escalation and agent workflow | Manage the durable customer-to-human handoff | Issues and registers submission IDs before confirmation; binds each ID to the customer and operation. Atomically saves confirmed content and a replay receipt through M9. Enforces ownership and state transitions. Acknowledges only committed results and distinguishes failed from uncertain saves. | B11/B13; C4/C5; B17 remains consolidated into B11 |
| M7 | Customer-data adapter | Limit access to the existing customer database through a stable boundary | Provides a read-only, authorized lookup of customer_id and account_status for the initial account-status use case. Returns a deterministic application response without model generation. General questions need no lookup. Customer-database fields are not sent to the AI provider. | Production addition P02; B04/B09; C7 |
| M8 | Feedback and reviewed improvement | Turn permitted feedback/patterns into evaluated, controlled improvements | Accepts permitted feedback linked to the inquiry, including fallback outcomes without an answer. Reviewers evaluate proposed changes; approved source updates use M3/C8 and approved generation configuration uses M4. Vlad coordinates release/rollback approval. No automatic training or unrestricted conversation retention is assumed. | B13/B16; production addition P04; C6 |
| M9 | Persistence adapters | Provide durable storage through component-owned data interfaces | Proposed shared PostgreSQL storage covers approved knowledge, support requests and replay receipts, permitted feedback, sessions and shared breaker records/leases. Business components own their records and rules; other modules use their interfaces. Raw conversation retention requires a separate decision. | B06/B11/B13; durable interfaces for knowledge, support, feedback, sessions and shared breaker state |

## Backlog and Unit 3 scope

These nine responsibilities are derived from the team backlog with Unit 3 design additions. M7 customer-database integration is a Unit 3 addition. M6 agent assignment/states, M8 governed improvement/versioning, and production admission/isolation policies extend the prototype backlog. B13/B14 feedback, request review and document administration are later full-backlog items, outside the four-week B01–B12 extract. These additions do not by themselves create new team implementation commitments.

## External boundaries

The external AI provider and existing customer database sit outside the application boundary. Browsers are untrusted. Proposed authentication uses opaque server-side sessions in Secure, HttpOnly, SameSite=Lax cookies, with CSRF protection on state-changing requests. Every protected action checks role and record scope. Idle/absolute expiry, logout scope and identity provisioning remain to be specified.

M9 provides component-owned persistence interfaces over proposed shared PostgreSQL. M3, M6 and M8 retain control of their data rules. Application replicas share session, receipt and breaker state; the existing customer database stays separate and read-only.

M2 supplies verified C9 access context to protected internal operations and a correlation ID for safe diagnosis. Browser-provided identity/role fields are not authority. C9 credentials/context are not sent to the external model. Document administration does not grant customer-support access. Operational logs avoid unnecessary raw questions and customer data.

Source-ID and access checks are structural checks. Whether a passage actually supports an answer needs a separate evaluation policy and review; valid links alone do not guarantee factual correctness.

## Boundaries to settle with the team

| Person | First review needed |
| --- | --- |
| Vlad | Confirm the service-level denominator, deployment proposal and cross-component boundaries; reconcile diagram, contracts and rationale for one final team review. |
| Hanlin | Align C1–C10 schemas, authorization and errors. Specify session expiry/logout/provisioning, server-issued submission-ID registration and expiry, ownership/version conflicts and atomic persistence contracts. |
| Collins | Provide provider/model quota evidence, allowed AI input/output, executable C10 evidence checks, and the shared-breaker counter/reset/write policy. |
| David | Verify denominator-aware service-level tests, expired/unknown ID and duplicate races, session/ownership isolation, and shared-breaker concurrency/recovery across replicas. |

## Implications of the selected workload

M1–M9 are logical modules, not nine services. The production proposal replicates one modular Flask application behind a load balancer and uses shared PostgreSQL state. Bounded AI admission avoids an application waiting queue. The proposed service level is 95% of eligible inquiries answered within 15 seconds, with a 20-second deadline. Provider, replica/database sizing and support limits require evidence.
