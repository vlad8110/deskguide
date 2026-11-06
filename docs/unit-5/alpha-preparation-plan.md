# DeskGuide alpha preparation and delivery plan

Prepared November 5, 2026. Coordinator: Vladimyr Merci. Proposed assignments and team checkpoints below require member confirmation.

The [module assignments and integration handoff](module-handoff.md) maps these responsibilities to existing files, planned service modules and concrete acceptance evidence.

## Goal and dates

Use the rest of Week 4, November 5–10, to build the first integrated alpha. Use Week 5, November 11–17, for formal peer review, fixes, clean setup, release evidence and individual reports. The first end-to-end workflow should run before Week 5 starts.

The [Unit 5 assignment](https://learn.umgc.edu/d2l/le/lessons/1541050/topics/37352195) requires a shared repository containing a functional, integrated alpha with an operational AI component, a passing CI/CD pipeline, meaningful collaborative history and installation/usage instructions. Each member must formally review one teammate’s module and submit an individual report of exactly 250 words explaining changes made from feedback and technical debt mitigation.

Use **Tuesday, November 17, 11:59 p.m. Eastern** as the planning cutoff because the assignment instructions specify Tuesday at that time. The live [submission folder](https://learn.umgc.edu/d2l/lms/dropbox/user/folder_submit_files.d2l?db=1995125&ou=1541050) displayed **November 18, 1:59 a.m.** when checked November 5. Finish the submission materials by **November 17, 8 p.m. Eastern** as a proposed team target, leaving a buffer before the earlier deadline. Other dates below are proposed internal checkpoints, not additional course deadlines.

## Starting point and first decisions

- [PR #15](https://github.com/vlad8110/deskguide/pull/15) contains the November 6 C4 combined design at `bf6e11dcf420f042c3384d5ae3cb3494d9e0d257`; peer approval is still pending. [The reconciliation](https://github.com/vlad8110/deskguide/blob/bf6e11dcf420f042c3384d5ae3cb3494d9e0d257/docs/unit-3/review-reconciliation-nov5.md) identifies the incorporated PR #16/#18 changes and remaining evidence.
- The local Flask/SQLite/C9 foundation now runs with account provisioning, browser sign-in/sign-out and automated foundation tests. See the [foundation handoff](../foundation.md). The project-check workflow is included, with hosted results tracked in the pull request checks. AI/product integration remains outstanding; the full alpha is not complete.
- Confirm the exact design baseline, team availability, remaining effort and module owners by November 6. Foundation development is underway; fixtures, UI and integration work should follow the agreed contracts and peer review.
- Agree that the alpha is the bounded Python/Flask/SQLite local prototype using fictional data. Retain the PostgreSQL/replicated-production design and 10,000-customer capacity requirement as separately identified design/validation work. A local demonstration does not establish that capacity. Any different required implementation scope must be settled before dependent work begins.
- Keep the existing [refined backlog IDs](../backlog/refined-eight-week-backlog-v2.md) and [implementation map](../backlog/implementation-map.md). Their planning-week labels are stages, not a reason to postpone unfinished dependencies. The four-week extract covers B01–B12; the alpha also needs B13–B15 and early setup/documentation work from B19/B20.
- Where the historical backlog uses employee/admin roles or answer-only feedback, implement the current C3 contracts: customer, agent and document-admin permissions are separate; document administration does not grant support-record access, and feedback belongs to an owned inquiry even when no answer exists. Keep B12 manual answer evaluation separate from the C1 service-target measurements.

## Minimum working alpha

Confirm this acceptance list with the team, retaining the approved MVP rather than silently dropping features.

| Capability | Observable evidence | Backlog / contract |
| --- | --- | --- |
| Repeatable startup | A teammate installs from a clean checkout, initializes temporary/demo data and starts the app using the README. No private environment or database is required. | B06; B19/B20 setup portions |
| Controlled access | Seeded demo accounts and server-enforced customer/agent/document-admin permissions; invalid session and cross-user access are denied. Use current C9 permissions rather than client-selected roles. | B09; C9 |
| Supported question | Browser → authorized retrieval → C10 prepare_evidence → ready expectation → real selected provider → C10 validate → answer with source links that open the exact permitted section/version. | B02/B07/B08/B10; C1/C2/C3/C10 |
| Honest fallback | Unsupported/ambiguous queries, missing evidence, provider timeout/quota/configuration failure and rejected answers return the agreed controlled outcome. Failed/unavailable precheck makes zero provider calls. | B11; B17 remains consolidated into B11 |
| Confirmed support | The customer can edit/cancel/confirm a support request. It is acknowledged only after durable saving, is retrievable by the authorized agent, and same-ID retry does not create a second record. | B11/B13; C4/C5 |
| Feedback and source management | Save feedback for the owned inquiry, including a no-answer outcome; provide the bounded authorized request/source review and document-management paths selected for the MVP. Changed sources retain stable identity/version behavior. | B13/B14; C2/C5/C6/C8 |
| Account-status demonstration | If retained in the alpha scope, use a fictional read-only adapter and trusted customer scope; return the fixed account-status response without retrieval or a model call. Record inclusion/exclusion explicitly at scope confirmation. | P02; C1/C7/C9 |
| Automated quality checks | The Unit 4 pipeline installs dependencies and executes meaningful tests, lint/style checks and a startup/integration smoke check on PRs. Retain run URLs and results. An empty test collection is not success. | B04/B09/B11/B12/B15; Unit 4 pipeline |

CI may use a deterministic provider substitute to test boundaries without secrets or paid calls. Alpha acceptance also needs a small, permitted demonstration of the actual selected AI provider with recorded model/configuration and outcomes. A mock-only path or canned answer is not evidence of operational AI integration. Do not put a live provider key or live requests into ordinary pull-request tests.

## Proposed ownership and handoffs

| Owner | Work to start this week | Handoff and completion evidence |
| --- | --- | --- |
| Vlad — Lead Architect and coordinator | B06 Flask app factory, configuration and SQLite schema; C1 orchestration, C9 access/session enforcement and persistence boundaries; coordinate support/feedback backend integration with Hanlin. Resolve interfaces and keep one integrated branch ready. | A clean startup command, demo seed data, working routes and persistence, small reviewed PRs, and an integrated end-to-end demo. Coordinate scope and readiness without taking over everyone’s implementation. |
| Hanlin — Interface Designer | B08 question/result/citation views, loading/error states and contract compatibility; B11 support preview/edit/cancel/confirm and authorized agent view; B13 feedback and B14 minimal document-admin interface. Implement against the agreed fixture responses while backend integration proceeds. | Browser flows connected to real endpoints, validation/access/error-state checks, and installation/usage screenshots or instructions. Agree backend/UI ownership with Vlad before editing shared files. |
| Collins — Integration Lead | B02 fictional sources and reviewed evidence manifest; B05 compare the two already shortlisted provider options and recommend one permitted free demonstration model; B07 retrieval and source lookup; B10/C3 provider adapter and C10 precheck/postcheck; B11 controlled failure handling. | Stable source/section/version IDs, 20 labeled questions with exact evidence, provider/configuration/quota notes, no secret in Git, one supported live flow and controlled failure examples. Share fixture shapes and adapter interfaces early. |
| David — Solutions Engineer | Independently review Collins’s fixtures; implement meaningful pytest/contract/security/integration cases and the GitHub Actions checks with Vlad; B12 evaluation and B15 alpha verification, defect reproduction and debt tracking. | Passing test run evidence, denied-access and duplicate-save cases, zero-call precheck tests, observed answer/source results and actionable review findings. Confirm capacity promptly; Vlad covers CI setup if availability is limited, without recording unperformed work as David’s contribution. |

Each person posts available hours, the remaining estimate for their work, one first deliverable and any blocker by November 6. The older B01–B12 estimates total 51–74 team person-hours for those stages; they are not a fresh estimate of remaining work and exclude later alpha tasks. Re-estimate the actual unfinished scope and reviews before committing the calendar.

## Proposed delivery checkpoints

| Date | Team result | Owner / decision |
| --- | --- | --- |
| Thu–Fri, Nov 5–6 | Confirm C3, bounded MVP, ownership, availability and review partners. Agree the shared request/response fixtures and source manifest shape. Review the local runnable foundation and connect its tests to CI. | Vlad coordinates; everyone confirms. David/Vlad establish CI; Collins starts fixtures/provider evidence; Hanlin starts views against fixtures. |
| Sat–Sun, Nov 7–8 | Deliver small module PRs and connect the first browser-to-retrieval-to-provider-to-validated-answer path. Basic permissions and source links work. Review as modules arrive. | Vlad integrates; Collins owns evidence/provider; Hanlin owns browser flow; David tests the boundaries. |
| Mon, Nov 9 | Demonstrate one permitted supported answer through the real provider and one failed/unavailable precheck with zero provider calls. Freeze fixture IDs and record the independent review. | Collins and David supply evidence; Vlad/Hanlin resolve integration defects. |
| Tue, Nov 10 | First integrated alpha: supported answer, controlled provider failure, customer-confirmed saved/retrievable support request, access denial, feedback and agreed document-management path. Pipeline passes from the integrated code. | Whole team. Escalate missing core functionality immediately rather than describing isolated modules as a working alpha. |
| Wed, Nov 11 — Unit 5 Day 1 | Hold the required team setup meeting; reconfirm roles and MVP, demonstrate the current build, and agree the remaining fixes and review assignments. | Vlad coordinates. Collect actual progress and blockers. |
| Thu–Fri, Nov 12–13 | Each member completes a formal review of another member’s code module and receives actionable feedback on their own work. Log findings, severity and proposed fixes. | Proposed review cycle below; everyone participates. |
| Sat–Sun, Nov 14–15 | Apply feedback, retest defects and record actual technical debt/mitigation. Run the 20-question evaluation and clean-checkout installation. Freeze a release candidate by Nov 15. | Module owners fix; independent reviewers verify; David consolidates test evidence. |
| Mon, Nov 16 | Final integration/regression and repository-access check; agree the exact alpha commit/release, README, known limitations and evidence links. Each member finishes the exactly 250-word report based on actual feedback and changes. | Vlad coordinates release candidate; everyone checks their own report and contribution. |
| Tue, Nov 17 | Resolve final blockers and prepare the shared repository link plus individual reports by the proposed 8 p.m. Eastern target. Complete the required LEO submissions before the earlier 11:59 p.m. Eastern planning cutoff. | Confirm whether each member must include the repo link; everyone remains responsible for their individual report/submission. |

The critical dependency is **approved scope/contracts → runnable app and fixtures → real integrated answer/fallback → meaningful CI and peer review → fixes and clean setup → identified alpha version and reports**. Fixture/interface work, UI work and test scaffolding can run in parallel once their boundaries are agreed. Integrate every day rather than saving all merges for the final week.

## Proposed formal review cycle

| Reviewer | Teammate module reviewed |
| --- | --- |
| Vlad | Hanlin’s browser and interface module |
| Hanlin | Collins’s retrieval/provider/C10 module |
| Collins | David’s testing and CI module |
| David | Vlad’s application, access and persistence module |

Confirm the pairings against actual contributions and availability. Each review addresses readability, security, performance, cross-module compatibility and documentation. Each author records the feedback received, the actual change, a commit/PR link and the relevant retest. Reviewing someone else’s code alone does not document changes made to the reviewer’s own work for the Refinement Report.

## Working agreements and readiness

- Work locally on small branches and use ordinary human peer review before merge. Coordinate shared schema/orchestration changes with Vlad and contract changes with Hanlin. Keep decisions and evidence in GitHub; email is the notification.
- Put an observed defect or a chosen shortcut in a debt/defect record with owner, impact, mitigation, evidence and target date. Do not invent technical-debt instances or claim a planned fix has been made.
- If the first real-provider path is not working by November 9, or the integrated MVP/CI is not ready November 10, hold a same-day scope/blocker review. Reassign work or seek an approved scope adjustment; do not quietly drop required features or substitute mocks for operational AI.
- Keep broad production hosting, multi-company support, autonomous account changes, automatic retraining and automatic second-provider failover outside the existing bounded prototype. Record SQLite/local-deployment and exact-alias coverage limitations honestly. Do not claim 10,000-user capacity without measured evidence.
- Preserve each member’s meaningful code/test commits and review records. A passing pipeline, an independently reproducible local setup and observed acceptance results identify readiness; documentation or a green badge alone does not.
