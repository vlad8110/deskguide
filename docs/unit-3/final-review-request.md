# Combined design review — November 6 C4

Coordinator: Vladimyr Merci. Status: C4 correction ready for peer review; exact-version team approval remains pending. Previous review baseline: November 5 C3, `da470a0bcc5aae0901d429cdc4f3641d8dfb74b0`. [PR #15](https://github.com/vlad8110/deskguide/pull/15) identifies the exact current commit.

Candidate content fingerprint: `081ff6ffc2ed0484b2401572f429341e1c0a2ed03883bfda4e1f05c2378ddb6a`.

## Correction for review

David's [November 5 C3 review](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5789994604) requested one example correction before his final sign-off. The C1 supported answer now exactly matches the `DOC-003/s2/v3` source shown in C2a/C2b/C3. The final Interface Contracts PDF already contains the correct C1 example on page 15. See the [resolution record](pending-review-resolution-nov6.md) for addressed findings and the remaining owner decisions.

The C2 → C10 prepare_evidence → ready only → C3 → C10 validate → C1 flow, diagrams, evidence policy and technical contract boundaries are unchanged. The earlier flow confirmations remain evidence for that specific finding, not complete-package approval.

Review the [contracts](interface-contracts.md), [AI flows](ai-integration.md), [architecture and diagrams](architecture-first-draft/README.md), [rationale](design-rationale.md) and [verification alignment](david-verification-alignment-nov2.md). Reply with approval or specific corrections against the exact C4 commit identified in PR #15. A changed deliverable needs renewed review.

| Member | Review focus | Current decision |
| --- | --- | --- |
| Vlad | Coordinate the C1 example correction, current evidence and integrated review | Correction ready; candidate approval pending |
| Hanlin | Confirm the corrected C1 answer matches C2/C3 and C10, preserving contract compatibility | Pending |
| Collins | Confirm example/evidence consistency and retain the selected outbound, availability and response-stage rules | Pending |
| David | Recheck the specific C1 answer/source mismatch as availability permits | CHANGES_REQUESTED on C3; C4 correction ready; renewed decision pending |

## Evidence still needed

- Reviewed fictional manifest: source versions, canonical hashes, exact aliases, approved answers/excerpts and independently fixed labels. Until configured, answer validation fails closed.
- Exact provider/model/account choice, actual quotas, data controls and bounded live evaluation. Production capacity remains unproven.
- Owner availability and agreement on one identified final revision. Planned verification cases are not executed results.

Hanlin's accepted backup role is retained. Original submitted artifacts are preserved; they are separate from GitHub review and implementation readiness.
