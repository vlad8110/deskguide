# Vlad — first architecture working session

Lead: Vlad. Working proposal for discussion, not an approved architecture or measured capacity result.

## First session outcome

Agree what 10,000 concurrent customers do, identify the components and their responsibilities, and record questions for Hanlin, Collins and David. Use the [refined sprint](../backlog/refined-four-week-sprint-backlog.md) and [implementation map](../backlog/implementation-map.md) as the starting point. Do not discard earlier failure handling, authorization, source verification or duplicate prevention.

## 1. Workload proposal to review together

Define concurrency first as **10,000 simultaneously connected/active customer sessions**. These are illustrative steady-state workload alternatives, not confirmed product measurements or accepted limits:

| Scenario | Inquiry frequency per session | Aggregate inquiry rate | In-flight inquiries if average response time were 5 seconds |
| --- | --- | --- | --- |
| Light | One every 10 minutes | 10,000 / 600 = 16.7 requests/second | About 84 |
| Working baseline proposal | One every 5 minutes | 10,000 / 300 = 33.3 requests/second | About 167 |
| Busy | One every minute | 10,000 / 60 = 166.7 requests/second | About 834 |

The five-second average is an illustrative calculation input, not a target or result. Use arrival rate × average time to estimate steady-state in-flight work; burst behavior and long-tail responses need separate analysis. If every inquiry calls the model, model call demand initially equals inquiry rate. No quota, cost, cache-hit rate or server size is assumed adequate.

Questions for our review:

- Does the assignment need active sessions or 10,000 simultaneous requests? Treat the latter as a separate stress scenario until resolved within the design.
- Which workload should we size the design against, and what burst multiplier/duration is credible?
- What response-time and failure targets should David evaluate? Keep B05/B12's measured-target agreement rather than inventing a demonstrated promise.
- How many inquiries can be answered without an external model call, if any? Do not assume caching is safe across customers.
- What must happen when provider quota or capacity is exhausted? Design bounded queues, controlled overload and support fallback without promising an unlimited agent queue.

Record the selected assumptions in decisions.md after Vlad/team review. David owns validation design; Collins checks provider constraints and Hanlin checks API timeout/overload semantics.

## 2. Component proposal

| Component | Owns | Backlog link | Review question |
| --- | --- | --- | --- |
| Customer browser / agent console | Question/result/citation states and authorized agent views | B03/B08/B11/B13 | What may each role see and change? |
| Application/API and authorization | Validation, customer scope, orchestration and access decisions | B04/B06/B09 | Which contracts expose each use case? |
| Retrieval/source service | Permitted passages, stable IDs, source resolution | B02/B07/B14 | How do source versions and customer permissions propagate? |
| AI adapter | Bounded provider calls, structured results, controlled failures | B05/B10/B11 | What is sent externally and how are unsupported outputs rejected? |
| Escalation service | Customer-confirmed request, single-save ID, acknowledgement and agent state | B11/B13/P03 | How are retries, ownership and failed handoffs handled? |
| Customer-data adapter | Minimum authorized customer fields from existing database | P02 | Which fields/operations are permitted, and what happens when the database fails? |
| Feedback/improvement workflow | Feedback association, reviewed changes, evaluation/versioning | B13/B16/P04 | Who may approve an improvement, and how is it rolled back? |
| Persistence adapters | Durable metadata, feedback and support records | B06/B11/B13/P01 | Which prototype choices must change for production? |

Logical modules do not automatically mean eight independently deployed services. Compare deployment alternatives after agreeing on responsibilities. No production database/provider is selected by this inventory.

## 3. How we will execute together

1. Review the workload options and component proposal with Vlad; record choices and open questions.
2. Draft one normal inquiry walkthrough and one unsupported/provider-failure-to-agent walkthrough, keeping stable IDs and authorization explicit.
3. Have Hanlin map the interactions to C1–C7, Collins check AI/escalation/feedback flows, and David identify failure/capacity gaps.
4. Compare a modular application and independently deployed services against the chosen workload, junior-maintainer needs, timeline and operational burden. Verify authoritative pattern sources before selecting/citing a final design.
5. Produce editable diagram source, a readable rendering, responsibility descriptions and capacity assumptions for Saturday, October 31 at 6 p.m. Eastern.
6. Cross-review Sunday, resolve findings and assemble the 500-word rationale Monday, and verify the package before Tuesday, November 3 at 11:59 p.m. Eastern.

## First-draft acceptance

- [ ] Workload meaning, calculations, assumptions and unresolved capacity questions are explicit.
- [ ] Diagram shows boundaries, directional data flow and existing customer database/external AI connections.
- [ ] Supported/unsupported answering, provider failure, durable human escalation and reviewed feedback are traceable.
- [ ] B01–B12 and relevant later items are mapped; B17 is not counted twice.
- [ ] No prototype benchmark is presented as 10,000-customer proof.
- [ ] David's review findings and the exact reviewed version are recorded.
