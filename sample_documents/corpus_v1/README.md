# DeskGuide fictional corpus — draft 1

Owner: Collins Amponsah.
Status: pending independent review by David; not approved for runtime use.

## Contents

- DOC-001.v1.json: fictional password-reset guide, sections s1–s3.
- DOC-002.v1.json: fictional campus Wi-Fi guide, sections s1–s3.
- DOC-003.v3.json: fictional VPN guide, sections s1–s2.
- evidence_manifest.json: eight proposed exact aliases, answers and evidence ranges.
- evaluation_questions.json: twenty proposed evaluation cases.

The DOC-003/s2/version-3 example preserves the combined design wording.
All instructions are fictional demonstration content, not implemented product features.

## Evidence conventions

Source versions are positive integer strings in these fixtures.
Evidence offsets are zero-based Unicode code-point ranges [start,end)
into NFC-normalized section text, without collapsing source whitespace.
Question/answer matching uses NFC plus trimmed, collapsed whitespace,
preserving case, punctuation, numbers and negation.

## Evaluation labels

Eight exact aliases and four whitespace variants expect ready preparation
only after independent approval, with authorized exact source versions,
healthy checks and sufficient budget.

Four unlisted paraphrases have supporting knowledge but expect
insufficient_evidence under the strict alias policy. Count these as
supported-question coverage misses, not genuinely unsupported questions.

Four missing-knowledge questions expect insufficient_evidence.
All insufficient-evidence cases expect zero generation calls.
These are proposed expectations, not recorded execution results.

## Validation performed

A local consistency check passed for all source references, excerpt
ranges/text, unique normalized aliases and twenty case expectations.
This is not endpoint, retrieval, provider, latency or capacity evidence.

## Review and integration still required

David independently checks source wording, labels, answer support and
evidence ranges. Record review against an exact commit.

Vlad and Collins must agree source-grant combination and approved-version
selection. These files do not grant access or select active runtime versions.
The classification and runtime_enabled fields are descriptive fixture
metadata; they do not implement an authorization or activation mechanism.

Use the existing app/inquiry_types.py service boundaries for integration.
Authorized retrieval, source lookup, C10 checks, outbound policy, provider
controls and deterministic endpoint response fixtures remain separate work.
No database, application startup or provider configuration is changed.

After approval, lock the reviewed snapshot before evaluation. Changes
require a new identified revision and review.

## PR #21 review follow-up

The initial demo uses three fictional guides instead of the earlier
8–12-document target so the team can review every source and evidence
mapping before integration. The reduced scope is pending team acceptance.

Q01–Q20 remain the baseline. Of the 16 questions labeled supported,
12 are eligible under the strict alias policy: eight exact aliases and
four whitespace variants of existing intents. The other four supported
questions are coverage misses. The remaining four baseline questions
are unsupported. The 12/16 figure describes fixture eligibility, not
measured answer accuracy. Whitespace variants add no new intents.

Count the four supplemental questions and eight permission/version
scenarios separately. Q01–Q12 expect one provider call only after all
prechecks pass; a failed precheck expects zero. Q13–Q20 and all four
supplemental questions expect zero. These are fixture expectations.

### Proposed release identity and authority

The test pin hashes the exact UTF-8 section text with SHA-256, excluding
JSON syntax and any added newline. For a runtime release, the proposal
is to record SHA-256 digests of the exact reviewed UTF-8 file bytes,
including their existing whitespace and line endings. One release record
binds the evidence manifest and all three source files to their digests
and exact source versions. Verify the pins before use. Missing, retired,
or mismatched content blocks generation; never substitute a newer version.

Release approval does not grant document access. Retrieval and exact
citation lookup must enforce current grants, including after rollback.

Proposed authority, pending team confirmation: a designated release
authorizer other than the author approves the exact reviewed release.
Only that role may activate it or roll back to a previously approved
release after checking its pins and current eligibility. If no approved
release is eligible, leave runtime disabled. This PR does not activate
a release.
