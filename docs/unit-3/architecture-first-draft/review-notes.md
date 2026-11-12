# Team review

This architecture reflects the November 2 proposals for team review. Responses are due November 3 at 10:00 a.m. Eastern; I will consolidate them afterward. Unanswered technical items remain open. Final agreement and LEO submission remain pending.

## What this review copy covers

- DeskGuide customer-service scope and relationship to the team's refined backlog.

- Selected workload: 10,000 concurrent customer sessions, each generating one inquiry per minute on average, approximately 167 new inquiries per second.

- Nine logical component responsibilities, with backlog-derived work and Unit 3 design additions distinguished.

- Supported-answer and unsupported/provider-failure-to-human-support walkthroughs.

- Editable visual architecture diagram and full-size image preview.

## Remaining architecture work

Production deployment/storage, service targets, session/ID defaults, non-author release, retention and breaker policies are proposed above. Exact provider/model capacity, replica/database sizing, payload/in-flight/support limits, executable evidence rules and breaker update behavior still require owner evidence and agreement.

M5 performs runtime evidence and source validation under C10. B12 manual scoring is separate offline verification. The executable runtime evidence-support rule remains with Collins; valid source IDs alone do not establish correctness.

The [design rationale](../design-rationale.md) contains the current draft. Align its final wording with the agreed diagram and contracts after the response round.

## Requested team review

- Hanlin: reconcile C1–C10 with the proposed policies, request selectors, permissions, session/ID values and concurrency/measurement boundaries.

- Collins: supply exact provider/model capacity and data-policy evidence, executable evidence-support rules, breaker window/reset/write rules and timing/outcome confirmation.

- David: verify fixed labels and denominators, session/ID/ownership races, release independence, deletion/restoration and shared-breaker recovery; review one identified final version.

- Vlad: reconcile the architecture, contracts and rationale, resolve cross-component findings and coordinate final team review.

B13/B14 are later full-backlog items rather than commitments in the first four-week extract. Customer-database integration, detailed agent workflow and governed improvement are Unit 3 design additions. Automatic second-provider failover remains deferred and B17 remains consolidated into B11.

## Dates

Team response cutoff: Tuesday, November 3, 2026, at 10:00 a.m. Eastern. Consolidation and final-version review follow. Working submission cutoff: November 3 at 11:59 p.m. Eastern; final team agreement and submission remain pending.
