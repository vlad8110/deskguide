# Work plan and ownership

Vlad is the continuing coordinator. Any temporary delegation must be recorded in a GitHub issue/comment with its scope, delegate and duration. No rotating handoff is assumed.

| Owner | Account | Lead work | Completion evidence |
| --- | --- | --- | --- |
| Vladimyr Merci | @vlad8110 | Architecture, scaling design, combined specification and final consistency | Diagram source/render, capacity assumptions, reviewed specification |
| Hanlin Wang | @Henry-Wong001 | API and component contracts | Typed schemas, examples, validation, authorization and failure contracts |
| Collins Amponsah | @MrAmpossible | AI integration and data flow | Normal, unsupported, provider-failure, escalation and reviewed-feedback paths |
| David Warren | @dwarren10 | Quality and design verification | Requirement traceability, edge-case review, security and load-validation plan |

Owners coordinate their sections; everyone contributes and reviews. Vlad assembles the 500-word rationale from the team's design reasoning. David reviews architecture, Collins reviews interfaces, Hanlin reviews AI flows, and the whole team reviews the rationale.

## Delivery schedule

The [Week 3 delivery schedule](week-3-delivery-schedule.md) is the shared schedule for drafts, review, final agreement and Tuesday submission.

## GitHub workflow

1. Use your Unit 3 issue for status, acceptance criteria, blockers and links.
2. Branch from current main. Edit only related files and submit a pull request linked to the issue.
3. Ask the named peer to review; resolve comments before merge. Record actual decisions and contributions.
4. Keep source copies, links and approved final exports in GitHub. Use the [shared Google Doc and draw.io file](architecture-first-draft/README.md) for architecture review edits; reconcile them before refreshing repository snapshots. Do not maintain competing review documents or distribute draft PDFs.
5. Vlad assembles the reviewed final specification. Record all four approvals and the exact final commit/file. Check individual submission obligations before upload; retain actual confirmation afterward.

No member acceptance, completed work, review, or submission is implied by this plan. Use fictional examples and keep secrets/private data out of this public repository.

## Backlog execution

Use [the implementation/design map](../backlog/implementation-map.md) to link B01–B24 to section owners and acceptance evidence. [Vlad’s first working session](architect-first-session.md) prepares workload and component decisions. A documented task is not an implemented feature; attach code, reviewed artifacts and actual test results before marking it complete.
