# Work plan and ownership

Vlad is the continuing coordinator. Any temporary delegation must be recorded in a GitHub issue/comment with its scope, delegate and duration. No rotating handoff is assumed.

| Owner | Account | Lead work | Completion evidence |
| --- | --- | --- | --- |
| Vladimyr Merci | @vlad8110 | Architecture, scaling design, combined specification and final consistency | Diagram source/render, capacity assumptions, reviewed specification |
| Hanlin Wang | @Henry-Wong001 | API and component contracts | Typed schemas, examples, validation, authorization and failure contracts |
| Collins Amponsah | @MrAmpossible | AI integration and data flow | Normal, unsupported, provider-failure, escalation and reviewed-feedback paths |
| David Warren | @dwarren10 | Quality and design verification | Requirement traceability, edge-case review, security and load-validation plan |

Owners coordinate their sections; everyone contributes and reviews. Vlad assembles the 500-word rationale from the team's design reasoning. David reviews architecture, Collins reviews interfaces, Hanlin reviews AI flows, and the whole team reviews the rationale.

## Internal milestones — Eastern time

| Date | Milestone |
| --- | --- |
| Friday, October 30 | Confirm owners, availability, component boundaries and workload assumptions in kickoff issue |
| Saturday, October 31, 6 p.m. | First diagram, contract, AI-flow and verification drafts via pull requests |
| Sunday, November 1 | Combine and cross-review; resolve mismatched names, fields, paths and dependencies |
| Monday, November 2 | Correct findings; verify rationale word count/citations; record final member agreement |
| Tuesday, November 3 | Final package checks and required LEO submission before 11:59 p.m. |

## GitHub workflow

1. Use your Unit 3 issue for status, acceptance criteria, blockers and links.
2. Branch from current main. Edit only related files and submit a pull request linked to the issue.
3. Ask the named peer to review; resolve comments before merge. Record actual decisions and contributions.
4. Keep all active assignment source files and final exports in GitHub; do not create competing email/Drive versions.
5. Vlad assembles the reviewed final specification. Record all four approvals and the exact final commit/file. Check individual submission obligations before upload; retain actual confirmation afterward.

No member acceptance, completed work, review, or submission is implied by this plan. Use fictional examples and keep secrets/private data out of this public repository.
