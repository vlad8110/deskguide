# Unit 3 — David's architecture and interface design-review checklist

**Owner:** David Warren (@dwarren10), Solutions Engineer
**Issue:** [#14](https://github.com/vlad8110/deskguide/issues/14)
**Status (Nov 2):** Architecture PR #15, Hanlin's Draft 3.1 PR #17, and Vlad's review of PR #18 have **actual COMMENTED peer reviews** (linked below). This checklist and the [November 2 alignment addendum](david-verification-alignment-nov2.md) are proposals pending final combined review; reviewed drafts are not formal approvals or test evidence.

PR #15 has revised editable component/deployment diagrams and a rationale draft, PR #17 has C1–C10 Draft 3.1, and PR #16 has AI flow drafts. These artifacts are still separate and their final single-version reconciliation remains pending. Original XR items below are retained as design traceability, not assertions that the drafts lack the described feature.

| ID | Area / proposed reviewer comment | Severity | Lead | Required resolution evidence | Status |
| --- | --- | --- | --- | --- | --- |
| XR01 | Define **10,000 concurrent customers**: connected sessions versus 10,000 active model requests; choose baseline, mix, burst and capacity targets. | High | Vlad + David | Signed-off workload and saturation assumptions in decisions.md and diagram | Open decision |
| XR02 | Distinguish scaled production deployment and shared durable storage/session handling from local Flask+SQLite prototype; show external provider and database trust boundaries. | High | Vlad | Architecture component diagram and storage/admission design | Open review |
| XR03 | Map every arrow to C1–C10 and give typed/validated inputs, outputs, customer scope, correlation ID and authorized failure response. | High | Hanlin + Vlad | Diagram/contract consistency review | Open review |
| XR04 | C4 escalation: explicit customer confirmation, durable commit *before* success acknowledgement; pre-registered server-issued IDs, scoped receipts, atomic saved-content commit and conflict/unknown-commit behavior. | High | Hanlin + Collins | Typed C4 request/responses, persistence uniqueness, C5 agent access, failure path | Open review |
| XR05 | Customer-data C7: derive identity server-side; document field allowlist, read/write permissions, per-object/tenant isolation, timeout and no-data disclosure. | High | Hanlin + Vlad | C7 schema; cross-tenant deny scenario V14 | Open review |
| XR06 | C2/C3 retrieval and model: validate citation IDs **and source version** against retrieved authorized passages; reject model output unsupported by sources. | High | Collins + Hanlin | Source-grounding and insufficient-evidence paths | Open review |
| XR07 | Retrieved malicious instructions are inert data; model cannot grant authorization, execute DB queries or send secrets/customer data to unapproved destinations. | High | Collins + David | Trust-boundary diagram, adversarial fixture V04 | Open review |
| XR08 | Escalation on provider timeout/quota: preserve question, allow user edit/cancel, never create silent ticket; failed/unknown save response must be honest. | High | Collins + Hanlin | Detailed normal/error sequence and C4 status semantics | Open review |
| XR09 | R3 learning: governed feedback review, regression evaluation, versioned deployment/rejection and rollback, **no assumed auto-retraining**. | Medium | Collins | Feedback workflow, approval roles, retained version IDs | Open review |
| XR10 | Rationale: tie modularity/cohesion/low coupling to actual diagram and explain one material capacity vs operational tradeoff with authoritative source. | Medium | Vlad + all | Final exactly 500-word narrative and documented citation | Open review |
| XR11 | Error envelope and HTTP mapping remain consistent across diagram, C1–C10, AI flows: 400/401/403/404/409/429/503 and timeout/unknown-save cases. | High | Hanlin + Collins | Contract and flow comparison against exact commit | Open review |
| XR12 | Privacy from [Issue #8](https://github.com/vlad8110/deskguide/issues/8): minimize user question retention, show escalation consent, avoid sensitive logs and verify provider data-use policy before selection. | High | David + Collins + Hanlin | Reviewed privacy choice, outbound data and retention inventory | Open review |

## Review and rubric crosswalk

- **Diagram / notation (30 pts):** external AI/customer-data services, component arrows, trust boundaries, durable escalation and session/storage strategy (XR01–XR03).
- **AI and data flow (30 pts):** supported/unsupported answer, cited passages, human escalation, provider errors and reviewed feedback (XR04, XR06–XR09).
- **Contracts (50 pts):** C1–C10 typed schemas, object-level permission, safe validation/errors, retries, source IDs and bounded timeouts (XR03–XR08, XR11).
- **Separation, cohesion and coupling (50 pts):** independent auth/customer data/AI/escalation modules, mockable adapters, and justified deployment tradeoff (XR02, XR10).

## Review record — add only actual evidence

| Artifact | Reviewed commit / PR | Reviewer | Actual findings | Status |
| --- | --- | --- | --- | --- |
| Architecture, decisions and updated diagrams | [PR #15](https://github.com/vlad8110/deskguide/pull/15), first-revised scope | David | [Nov 1 COMMENTED review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5730726420) | Draft review done; final integrated version pending |
| C1–C10 interface contracts, Draft 3.1 | [PR #17 at 0e7f855](https://github.com/vlad8110/deskguide/pull/17) | David, Collins | [David Nov 2 COMMENTED](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5738959296); [Collins COMMENTED](https://github.com/vlad8110/deskguide/pull/17#pullrequestreview-5725100910) | Draft review done; residual decisions pending |
| Verification/security plan | [PR #18 at a9912c9](https://github.com/vlad8110/deskguide/pull/18) | Vlad | [Nov 2 COMMENTED review](https://github.com/vlad8110/deskguide/pull/18#pullrequestreview-5744463050) requested revised cases and metrics | This updated package responds; formal final approval pending |
| AI and escalation/feedback flows | [PR #16](https://github.com/vlad8110/deskguide/pull/16) | Team | Vlad's review requests alignment; David has not submitted final approval | Pending |
| 500-word rationale | [Vlad draft PR #15](https://github.com/vlad8110/deskguide/pull/15) | Whole team | Draft incorporated rationale input, no verified joint final approval | Pending |
| Final rendered specification | Pending final export | Whole team | No exact reviewed export or approvals documented | Pending |

## What should happen next

Vlad, Hanlin and Collins should reconcile the same final contract/diagram/AI version, with outstanding provider-policy, runtime evidence-support and production-breaker details explicitly identified. See [David's Nov 2 response](david-verification-alignment-nov2.md) for the planned N01–N15 cases, class-labeled B12 questions and denominators. David should verify the exact final export before any APPROVED review. No finding is closed solely because a proposal exists. **No test has been executed.**
