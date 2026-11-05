# Unit 3 review reconciliation — November 5

Coordinator: Vladimyr Merci. Review candidate: November 5 C3. Combined-version approval remains pending.

## Source revisions

| Source | Current head inspected | Disposition in the combined candidate |
| --- | --- | --- |
| [Architecture and combined design, PR #15](https://github.com/vlad8110/deskguide/pull/15) | November 3 C2, `5828ddf284d4c03a5a53e447eff8512060bb42a9`, plus the November 3 shared-source correction | A3b and M5 explicitly show the pre-generation evidence gate and post-generation validation. |
| [Collins’s AI flows, PR #16](https://github.com/vlad8110/deskguide/pull/16) | `0099cd842ff02463f6ad6adf5ff4e887fb501280` | The revised flows are incorporated with the coordinator’s inquiry-bound expectation, availability counting, response-stage rules and accepted Hanlin backup. |
| [David’s verification package, PR #18](https://github.com/vlad8110/deskguide/pull/18) | `d3295e7f341a26812620e66a0878ec554291625e` | Latest V01/V02/X01 and XR06/XR13 wording incorporated without replacing the newer combined contributions, backup assignment or N16–N21 checks. |

No newer head commits were present on these three PRs at inspection on November 5. [Hanlin’s contracts, PR #17](https://github.com/vlad8110/deskguide/pull/17), at `253be0deb5f3f96b75373de9925e4df8d4035d97`, remain the source for the combined Draft 3.3 contracts; this reconciliation does not modify his branch.

## Alignment and remaining evidence

| Topic | Combined design and planned verification | Remaining action |
| --- | --- | --- |
| Evidence order | C2 permitted retrieval → C10 prepare_evidence → ready expectation only → C3 → C10 validate using that expectation → C1 display. Failed or unavailable precheck makes zero provider calls and never silently saves support. V01/V02/X01, XR06/XR13 and N16/N17 cover this boundary. | David [confirmed the specific documentation finding resolved](https://github.com/vlad8110/deskguide/pull/15#issuecomment-6618357810); Collins [confirmed flow consistency](https://github.com/vlad8110/deskguide/pull/15#issuecomment-6618837185). Obtain approval of the exact combined revision. Runtime checks remain unexecuted. |
| Extractive evidence policy | One reviewed alias selects an approved answer before generation; all required source versions/excerpts must be present, and the generated wording must match exactly. An extra model call, fuzzy acceptance or automatic retry is not part of this policy. | Collins supplies canonical synthetic source text, hashes, exact aliases, excerpt offsets and approved answers. An independent reviewer locks the fixtures and eligibility labels before activation. |
| Provider availability and service quality | A well-formed completed provider response contributes to N even when C10 rejects the answer; that rejection is excluded from provider failures F but remains an AI-service miss. No-dispatch denials are not completed provider calls. N18 covers the distinction. | Collins and David verify the proposed counters, race/recovery rules and examples against the same configuration; measured results remain outstanding. |
| Responses and deadlines | Pre-admission denial is 503 with Retry-After; admitted C3 failure is controlled 200 unavailable; overall deadline expiry is 504. Overall budget is 20 seconds, provider wait at most 12 seconds with a one-second fallback reserve. No AI waiting queue or automatic generation retry. | Recheck C1/C3 and N19 against one final revision. Provider/account quotas and actual latency remain unverified. |
| Support, identity and release | Server-registered IDs, durable receipt before acknowledgement, no automatic replacement ID after uncertain save, deterministic read-only account status, and non-author release authorization remain aligned. Hanlin is the accepted backup; David declined that duty. | Keep accepted-backup and current contribution records when integrating either teammate branch. Explicit permissions, implemented controls and executed cases remain outstanding. |
| Capacity and completion | The design assumption is 10,000 active sessions averaging one inquiry per minute. N15 plans controlled synthetic load; B12 is an independent manual evaluation and does not replace runtime C10 validation. | Obtain exact provider/model/account controls and quotas, resource sizing, fixture review and executed tests before claiming working functionality or production capacity. |

## Recommended integration and review

1. Use the corrected combined PR #15 candidate for one independent review of architecture, contracts, AI flow and verification together.
2. Collins checks that the combined AI text preserves his intended policy while retaining the selected expectation, N/F, status and backup clarifications. David checks the imported sequence rows and the retained N16–N21 additions as availability permits; Hanlin checks C10/C1/C3 compatibility.
3. Preserve each member’s source commits and contribution evidence. PRs #16 and #18 both change contributions.md; David’s branch also changes decisions and the verification addendum. Merging the older branch files over the combined copies would regress accepted-backup and contribution information.
4. After the combined revision is approved and integration is authorized, merge the consolidated work once. Close overlapping source PRs as incorporated only after confirming every relevant change is preserved and linking the accepted combined revision. Do not treat a merge without textual conflicts as proof that the content is reconciled.

The recorded reviews are COMMENTED rather than APPROVED. The two flow confirmations do not establish complete-package approval, test execution or provider capacity.
