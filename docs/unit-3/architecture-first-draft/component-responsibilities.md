# Unit 3 — Component responsibilities

Author: Vladimyr Merci. Working snapshot of the [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit). Make team edits there; refresh this repository copy before publishing a new revision. Team approval is pending.

Working basis: scope statement and selected workload: 10,000 concurrent customer sessions generating approximately 167 new inquiries per second. These components describe responsibilities; deployment choices and capacity evidence remain to be developed.

## Component proposal

I propose separating DeskGuide into the following logical components. Each component has one main responsibility and communicates through a defined interface. These boundaries will guide the architecture diagram and the team's contracts.

| ID | Component | Main responsibility | Information and interactions | Backlog / contract alignment |
| --- | --- | --- | --- | --- |
| M1 | Browser interfaces | Present customer questions/results, human-agent work, and authorized administration | Sends user actions to the application; displays citations, loading/error states, escalation confirmation and saved-request acknowledgement. Screens do not determine authorization. | B03/B08/B13/B14; C1/C4/C5/C6 |
| M2 | Application and access control | Validate requests, enforce permissions and customer scope, and coordinate use cases | Establishes trusted identity/role context; calls only the services permitted for that user. Applies admission limits and communicates controlled overload. Browser-supplied role/customer identifiers are not trusted as authority. | B04/B06/B09; authorization across C1–C7 |
| M3 | Knowledge and retrieval | Manage approved knowledge versions and retrieve only passages the caller may access | Returns ranked passages with stable document, section and version identifiers; serves authorized source sections. Document administration is a separate privileged operation within this boundary. | B02/B07/B14; C2; document-management contract needs definition |
| M4 | AI provider adapter | Isolate external generation and provider-specific failure behavior | Receives permitted question/context/passages and returns a structured candidate answer or controlled failure. Enforces configured deadlines and call limits; keeps credentials server-side. It does not decide authorization or save support requests. | B05/B10/B11; C3 |
| M5 | Answer and source validation | Check candidate output and citation structure under a defined policy | Checks source identifiers, versions, permitted access and resolvability. Runtime evidence-sufficiency policy remains proposed; valid citations do not prove semantic correctness. B12 manually evaluates answer support. | B07/B10 structural checks; B12 manual evaluation; C1/C2/C3; internal contract needs definition |
| M6 | Escalation and agent workflow | Manage the durable customer-to-human handoff | Saves only customer-confirmed content, assigns a stable submission/request ID, prevents duplicate saves on retry, acknowledges the saved result and controls agent ownership/state transitions. Handles failed saves and queue limits explicitly. | B11/B13; C4/C5; B17 remains consolidated into B11 |
| M7 | Customer-data adapter | Limit access to the existing customer database through a stable boundary | Accepts trusted customer scope and permitted operations; returns only required fields or a controlled unavailable/denied result. The AI provider has no direct database connection. Exact fields and any permitted updates need review. | Production addition P02; B04/B09; C7 |
| M8 | Feedback and reviewed improvement | Turn permitted feedback/patterns into evaluated, controlled improvements | Associates feedback with the answer/source version; authorized reviewers propose and evaluate changes before publication. Records versions and rollback decisions. Feedback is not automatic model retraining or permission to retain every conversation. | B13/B16; production addition P04; C6 |
| M9 | Persistence adapters | Provide durable storage through component-owned data interfaces | Stores approved knowledge metadata, confirmed support requests and permitted feedback/review records. Each business component owns its records and rules; other components use its interface rather than editing its tables. Ordinary raw conversation retention requires a separate decision. | B06/B11/B13; storage operations supporting C2/C4/C5/C6 |

## Backlog and Unit 3 scope

These nine responsibilities are derived from the team backlog with Unit 3 design additions. M7 customer-database integration is a Unit 3 addition. M6 agent assignment/states, M8 governed improvement/versioning, and production admission/isolation policies extend the prototype backlog. B13/B14 feedback, request review and document administration are later full-backlog items, outside the four-week B01–B12 extract. These additions do not by themselves create new team implementation commitments.

## External boundaries

The diagram will place the external AI provider and existing customer database outside DeskGuide's application boundary. Customer, agent and administrator browsers are untrusted clients. Authentication details remain a design decision; every protected action requires server-side authorization and customer/record scope checks.

M9 represents storage interfaces, not a decision to use one physical database or to share tables freely. M3, M6 and M8 retain ownership of their data behavior. We will decide the production database and deployment topology after assessing the workload and failure requirements.

Each important interaction will carry a correlation/request identifier and trusted access scope, with explicit data ownership, retention and failure semantics. Document-administration rights do not automatically grant access to customer conversations or support requests. Operational logs should support diagnosis without unnecessarily recording raw questions or customer data.

Source-ID and access checks are structural checks. Whether a passage actually supports an answer needs a separate evaluation policy and review; valid links alone do not guarantee factual correctness.

## Boundaries to settle with the team

| Person | First review needed |
| --- | --- |
| Vlad | Check responsibilities and dependencies; decide which logical boundaries belong in the first diagram. |
| Hanlin | Map interactions to C1–C7; add or extend contracts for authentication/access context, privileged document management and internal answer validation. Specify fields, permissions, deadlines and errors. |
| Collins | Confirm the AI adapter's allowed input and structured output, answer-validation policy, and failure/escalation/feedback interactions. |
| David | Review cross-customer access, invalid citations, provider failure, duplicate requests, failed saving, and overload behavior. Define how each boundary will be verified. |

## Implications of the selected workload

The nine logical components do not imply nine services, servers or separately deployed processes. We will use the approximately 167-inquiries-per-second assumption to assess which operations can run independently, which need shared durable state, and where provider/database/agent capacity could limit the system. Replica counts, queue bounds, timeouts and latency targets remain open design decisions.
