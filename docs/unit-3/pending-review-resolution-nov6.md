# Pending design review resolution

```text
********************************************************************************
* Created: 2026-11-06                                                          *
* Created by: Vladimyr Merci                                                   *
* Updated: 2026-11-06                                                          *
* Purpose: Close the remaining design-review findings and identify owner       *
* decisions needed for the implementation handoff.                             *
* Participants: add your name, date, completed work and tools actually used.   *
********************************************************************************
```

Coordinator: Vladimyr Merci. Review revision: November 6 C4, derived from November 5 C3 (`da470a0bcc5aae0901d429cdc4f3641d8dfb74b0`). See [PR #15](https://github.com/vlad8110/deskguide/pull/15) for the exact current commit. Renewed peer review remains pending. This record does not mark a teammate's approval or unexecuted test complete.

## Correction ready for review

David's [November 5 change request](https://github.com/vlad8110/deskguide/pull/15#pullrequestreview-5789994604) verified the C3 evidence order, bound expectation, availability counting, response-stage rules, outbound boundary and diagrams at the design-documentation level. His remaining concrete correction is the C1 supported-answer example: its wording must match the shown `DOC-003/s2/v3` source under the exact-excerpt policy.

The [C1 example](interface-contracts.md#c1-customer-inquiry-and-answer) now uses the same wording as C2a, C2b and C3:

> Install the Acme VPN client, sign in, and select the Campus profile.

The [final Interface Contracts PDF](https://drive.google.com/file/d/1aSrxqOmHQj9-oV2i3wiOu-L_uuPesqaz/view) already uses this exact sentence in its C1 example on page 15. Its Word companion also contains the corrected text. The source correction aligns the repository snapshot with those final artifacts; it does not require replacing the PDF for this finding. Original submission artifacts remain preserved.

Hanlin reviews the correction against C10; David can recheck C4 as availability permits. David requested changes on C3. The correction does not constitute his approval; the new review decision must come from him.

## Completion checklist

- [x] Correct the C1 answer to match its exact versioned source example.
- [x] Confirm the final contracts PDF already has the correct answer on page 15.
- [x] Reconcile the pre-generation and post-generation C10 order with the documented flow confirmations.
- [x] Record Hanlin's accepted backup role and David's declined additional duty.
- [x] Assemble the specification, contracts and 500-word rationale and record Vlad's Unit 3 submission receipt.
- [ ] Obtain the renewed C4 review decision and remaining exact-version member approvals.
- [ ] Populate and independently review the fictional source/evaluation manifest.
- [ ] Confirm the provider/model/account and actual controls, limits and evaluation results.
- [ ] Execute the remaining implementation, privacy, integration and capacity checks appropriate to their scope.
- [ ] Merge the accepted combined revision and reconcile overlapping PRs after approval.

## Findings already addressed in the combined design

| Finding | Evidence and disposition |
| --- | --- |
| Missing pre-generation gate in the walkthrough/diagram | A3b and M5 show permitted retrieval → prepare_evidence → ready only → generation → validate → display. David [confirmed the specific order resolved](https://github.com/vlad8110/deskguide/pull/15#issuecomment-6618357810); Collins [confirmed flow consistency](https://github.com/vlad8110/deskguide/pull/15#issuecomment-6618837185). Those confirmations do not approve the full package. |
| Interface/flow disagreements raised by Hanlin and Collins | C3 includes server-registered escalation/reply IDs, uncertain-save recovery, current state names, 30-minute/eight-hour sessions, the combined three-ID cap, explicit account-status routing, provider-context isolation and the 200/503/504 distinction. David's November 5 review verified the key combined design boundaries. Exact-version owner approval is still required. |
| Provider response counting and C10 rejection | C3 distinguishes completed provider calls N from provider failures F and separate AI-service misses. C10-rejected completed responses remain in N, not F. N18/N19 are planned implementation checks. |
| Backup release-authorizer assignment | David declined the extra backup role; Hanlin accepted the replacement role. Current combined documents identify Vlad as primary and Hanlin as backup, preserving independent non-author authorization. Current coordination names Hanlin as backup; original source comments remain historical evidence. |
| Submission status | Vlad's Unit 3 submission was received November 3. Submission does not establish final team approval, other members' submissions, a grade or implemented capacity. Each member remains responsible for their required individual submissions. |

## Decisions and evidence still needed

| Item | Responsible handoff | What closes it |
| --- | --- | --- |
| Exact-version approval | Vlad coordinates; Hanlin, Collins and David review their boundaries | Use the corrected candidate's exact published commit and collect each actual review decision. Do not substitute the earlier flow-only confirmations. |
| Fictional source/evaluation manifest | Collins authors; David or another confirmed independent reviewer checks; Vlad arranges coverage | Canonical sources, hashes, stable section/version IDs, aliases, approved exact answers/excerpts and fixed supported/unsupported/ambiguous labels. The proposed 12/4/4 split remains subject to agreement. |
| Provider/model decision and account evidence | Collins, with Vlad coordinating | Exact demonstration model/account/tier, permitted terms, actual data controls, quotas/token/concurrency limits, cost and a bounded live comparison. Existing research does not select or validate a provider. Keep prototype data fictional. |
| Outbound policy and notice | Vlad selects scope; Collins confirms provider behavior; Hanlin implements the notice; David/confirmed reviewer verifies | Agree D22/D23 wording and allowed classifications, then prove enforcement and truthful notice before external submission. Customer/session/account fields remain outside generation. |
| Review/CI availability | Each member confirms capacity; Vlad coordinates coverage | Confirm available hours, first deliverable and blockers. David's completed design review is recorded; additional urgent work is not assumed accepted. |
| Integration of overlapping PRs | Vlad coordinates after approval | Preserve contributions and selected combined changes before merging PR #15 or closing PRs #16/#18 as incorporated. Hanlin's PR #17 source remains owned by Hanlin. |
| Issue status maintenance | Vlad coordinates | Link completed criteria to evidence, retain historical dates as history and keep unresolved criteria open. A checked documentation task does not record another member's approval. |

The [provider research](https://github.com/vlad8110/deskguide/issues/5), [privacy proposals](https://github.com/vlad8110/deskguide/issues/8), [Hanlin's follow-up](https://github.com/vlad8110/deskguide/issues/12), [Collins's follow-up](https://github.com/vlad8110/deskguide/issues/13) and [David's review evidence](https://github.com/vlad8110/deskguide/issues/14) remain the coordination sources. Research, designed controls and executed implementation results must retain their separate statuses.

## Handoff after the review closeout

The local Flask/SQLite/C9 foundation has its own automated tests. It does not implement retrieval, C10, the live provider, support/feedback services or a published CI workflow. Those implementation deliverables remain in the [backlog](../backlog/README.md) and role issues [#1](https://github.com/vlad8110/deskguide/issues/1), [#3](https://github.com/vlad8110/deskguide/issues/3), [#4](https://github.com/vlad8110/deskguide/issues/4) and [#6](https://github.com/vlad8110/deskguide/issues/6). The foundation and its local setup/handoff guides require their own publication; they are not included in this design-review correction.

Use one agreed contract baseline and shared request/response fixtures. Collins can prepare sources/services, Hanlin can develop interface states and David can review fixtures/tests while Vlad builds C1 orchestration. Collect actual owner availability and an independent setup result before committing the integration schedule.
