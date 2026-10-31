# Unit 3 — David's architecture and interface design-review checklist

**Owner:** David Warren (@dwarren10), Solutions Engineer  
**Issue:** [#14](https://github.com/vlad8110/deskguide/issues/14)  
**Status:** Draft review requests based on the current **working outlines** of [architecture](architecture.md), [C1–C7 contracts](interface-contracts.md) and [AI integration](ai-integration.md). These are proposed checks, **not completed peer review or confirmed defects**. Confirm outcomes against the exact reviewed PR/commit on November 1.

The architecture, interface-contract and AI-integration documents currently identify modules and planned flows but do not yet contain a finalized deployed component diagram, complete typed API contracts or the detailed approved AI sequence. This checklist preserves the questions that must be answered as those drafts mature.

| ID | Area / proposed reviewer comment | Severity | Lead | Required resolution evidence | Status |
| --- | --- | --- | --- | --- | --- |
| XR01 | Define **10,000 concurrent customers**: connected sessions versus 10,000 active model requests; choose baseline, mix, burst and capacity targets. | High | Vlad + David | Signed-off workload and saturation assumptions in decisions.md and diagram | Open decision |
| XR02 | Distinguish scaled production deployment and shared durable storage/session handling from local Flask+SQLite prototype; show external provider and database trust boundaries. | High | Vlad | Architecture component diagram and storage/admission design | Open review |
| XR03 | Map every arrow to C1–C7 and give typed/validated inputs, outputs, customer scope, correlation ID and authorized failure response. | High | Hanlin + Vlad | Diagram/contract consistency review | Open review |
| XR04 | C4 escalation: explicit customer confirmation, durable commit *before* success acknowledgement; stable ID, scoped idempotency key and conflict/unknown-commit behavior. | High | Hanlin + Collins | Typed C4 request/responses, persistence uniqueness, C5 agent access, failure path | Open review |
| XR05 | Customer-data C7: derive identity server-side; document field allowlist, read/write permissions, per-object/tenant isolation, timeout and no-data disclosure. | High | Hanlin + Vlad | C7 schema; cross-tenant deny scenario V14 | Open review |
| XR06 | C2/C3 retrieval and model: validate citation IDs **and source version** against retrieved authorized passages; reject model output unsupported by sources. | High | Collins + Hanlin | Source-grounding and insufficient-evidence paths | Open review |
| XR07 | Retrieved malicious instructions are inert data; model cannot grant authorization, execute DB queries or send secrets/customer data to unapproved destinations. | High | Collins + David | Trust-boundary diagram, adversarial fixture V04 | Open review |
| XR08 | Escalation on provider timeout/quota: preserve question, allow user edit/cancel, never create silent ticket; failed/unknown save response must be honest. | High | Collins + Hanlin | Detailed normal/error sequence and C4 status semantics | Open review |
| XR09 | R3 learning: governed feedback review, regression evaluation, versioned deployment/rejection and rollback, **no assumed auto-retraining**. | Medium | Collins | Feedback workflow, approval roles, retained version IDs | Open review |
| XR10 | Rationale: tie modularity/cohesion/low coupling to actual diagram and explain one material capacity vs operational tradeoff with authoritative source. | Medium | Vlad + all | Final exactly 500-word narrative and documented citation | Open review |
| XR11 | Error envelope and HTTP mapping remain consistent across diagram, C1–C7, AI flows: 400/401/403/404/409/429/503 and timeout/unknown-save cases. | High | Hanlin + Collins | Contract and flow comparison against exact commit | Open review |
| XR12 | Privacy from [Issue #8](https://github.com/vlad8110/deskguide/issues/8): minimize user question retention, show escalation consent, avoid sensitive logs and verify provider data-use policy before selection. | High | David + Collins + Hanlin | Reviewed privacy choice, outbound data and retention inventory | Open review |

## Review and rubric crosswalk

- **Diagram / notation (30 pts):** external AI/customer-data services, component arrows, trust boundaries, durable escalation and session/storage strategy (XR01–XR03).
- **AI and data flow (30 pts):** supported/unsupported answer, cited passages, human escalation, provider errors and reviewed feedback (XR04, XR06–XR09).
- **Contracts (50 pts):** C1–C7 typed schemas, object-level permission, safe validation/errors, retries, source IDs and bounded timeouts (XR03–XR08, XR11).
- **Separation, cohesion and coupling (50 pts):** independent auth/customer data/AI/escalation modules, mockable adapters, and justified deployment tradeoff (XR02, XR10).

## Review record — add only actual evidence

| Artifact | Reviewed commit / PR | Reviewer | Actual findings | Status |
| --- | --- | --- | --- | --- |
| Architecture diagram | Pending | David | Not reviewed yet | Pending |
| C1–C7 interface contracts | Pending | David / Collins | Not reviewed yet | Pending |
| AI and escalation/feedback flows | Pending | David / Hanlin | Not reviewed yet | Pending |
| 500-word rationale | Pending | Whole team | Not reviewed yet | Pending |
| Final rendered specification | Pending | Whole team | Not reviewed yet | Pending |

## What should happen next

Vlad, Hanlin and Collins should comment on their assigned questions in the relevant section PRs; David then records actual resolved findings with PR links and commit IDs in [verification-plan.md](verification-plan.md). No findings may be closed merely because they appear in this plan. **No test has been executed.**
