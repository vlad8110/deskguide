# Team review

*November 1 shared-source snapshot. Current direction: [November 2 proposed decisions](../proposed-decisions.md).*

Author: Vladimyr Merci. Status: proposed; team approval pending.

This architecture combines the current proposals for team review. Final agreement and LEO submission remain pending.

## What this review copy covers

- DeskGuide customer-service scope and relationship to the team's refined backlog.

- Selected workload: 10,000 concurrent customer sessions, each generating one inquiry per minute on average, approximately 167 new inquiries per second.

- Nine logical component responsibilities, with backlog-derived work and Unit 3 design additions distinguished.

- Supported-answer and unsupported/provider-failure-to-human-support walkthroughs.

- Editable visual architecture diagram and full-size image preview.

## Remaining architecture work

Production storage, deployment pattern, bounded admission and service targets are proposed above. Exact provider/model quotas, replica/database sizing, session lifetimes, unused submission-ID validity, payload/in-flight/support limits and capacity results remain pending.

M5 performs runtime evidence and source validation under C10. B12 manual scoring is separate offline verification. The executable runtime evidence-support rule remains with Collins; valid source IDs alone do not establish correctness.

The design rationale is available with the review log. Align its final wording with the agreed diagram and C1–C10 contracts.

## Requested team review

- Hanlin: finalize C1–C10, session/identity details, submission-ID registration/expiry and ownership/version conflicts.

- Collins: supply provider/model capacity evidence, runtime evidence-support policy and shared-breaker counter/reset/write details.

- David: verify the service-level denominator, expired-ID/duplicate races, session/ownership isolation and shared-breaker recovery.

- Vlad: reconcile the architecture, contracts and rationale, resolve cross-component findings and coordinate final team review.

B13/B14 are later full-backlog items rather than commitments in the first four-week extract. Customer-database integration, detailed agent workflow and governed improvement are Unit 3 design additions. Automatic second-provider failover remains deferred and B17 remains consolidated into B11.

## Dates

Internal combined review: Sunday, November 1; corrections and agreement: Monday, November 2. Working submission deadline: Tuesday, November 3, 2026, at 11:59 p.m. Eastern.
