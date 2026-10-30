# First draft review notes

Author: Vladimyr Merci. Working snapshot of the [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit). Make team edits there; refresh this repository copy before publishing a new revision. Team approval is pending.

I reviewed the first architecture draft and approved preparing it for team review. This working copy brings the four written drafts together with the reviewed diagram. Team approval and final LEO submission are still pending.

## What this review copy covers

- DeskGuide customer-service scope and relationship to the team's refined backlog.

- Selected workload: 10,000 concurrent customer sessions, each generating one inquiry per minute on average, approximately 167 new inquiries per second.

- Nine logical component responsibilities, with backlog-derived work and Unit 3 design additions distinguished.

- Supported-answer and unsupported/provider-failure-to-human-support walkthroughs.

- Editable visual architecture diagram and full-size image preview.

## Remaining architecture work

The workload is a design assumption, not a measured capacity result. Server/replica quantities, production storage, deployment pattern, provider quotas/costs, payloads, service targets, queue bounds and burst validation remain open. The selected workload is not a claim that 10,000 simultaneous requests can receive immediate answers.

B12 retains manual scoring of answer support and response time. Structural citation checks do not guarantee semantic correctness. The diagram's M5 label includes manual quality review as a verification responsibility; it must not be read as requiring a human to approve every live answer. Runtime evidence-sufficiency routing remains to be agreed with the team.

The architecture-pattern tradeoff and authoritative supporting citation still need to be selected and verified. This draft does not supply the team's final 500-word rationale or finished interface contracts.

## Requested team review

- Hanlin: align C1-C7 schemas, permissions, safe error behavior and retry identity with the component boundaries; identify missing contracts.

- Collins: review permitted model input/output, source checks, provider-failure routing, explicit human handoff and reviewed improvement flow.

- David: review requirement coverage, customer isolation, duplicate-save/uncertain-save behavior, workload assumptions and the planned capacity validation.

- Vlad: resolve cross-component findings, finish the deployment/capacity explanation and architectural tradeoff, then assemble the reviewed team specification.

B13/B14 are later full-backlog items rather than commitments in the first four-week extract. Customer-database integration, detailed agent workflow and governed improvement are Unit 3 design additions. Automatic second-provider failover remains deferred and B17 remains consolidated into B11.

## Dates

First draft target: Saturday, October 31, 2026, at 6 p.m. Eastern. Internal combined review: Sunday, November 1; corrections and agreement: Monday, November 2. Working submission deadline: Tuesday, November 3, at 11:59 p.m. Eastern.
