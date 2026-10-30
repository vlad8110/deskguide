# Interface contracts — working specification

Lead: Hanlin. Reviewers: Collins and David. Coordinate component names and boundaries with Vlad.
Status: contract framework awaiting concrete endpoints and values.

## Required contract inventory

| ID | Interaction | Required content |
| --- | --- | --- |
| C1 | Customer inquiry and answer | Auth/context, question, answer status, sources and correlation ID |
| C2 | Retrieval/source access | Query, allowed scope, ranked passage/source IDs and missing-source behavior |
| C3 | AI generation adapter | Allowed passages/context, structured answer, deadline and provider failure mapping |
| C4 | Human escalation | User-reviewed content, submission ID, durable acknowledgement, retry and duplicate handling |
| C5 | Agent review/update | Authorized access, request state, ownership and permitted transitions |
| C6 | Feedback/improvement | Answer/source version, feedback fields, review visibility and validation |
| C7 | Existing customer database | Minimum authorized customer fields, adapter signature and dependency failures |

## Fill out for every API or component method

- HTTP method/path or typed method signature; owner/caller and contract version.
- Authorization and permitted customer/document scope.
- Input/output names, types, required/optional/nullability rules, sizes, allowed values and constraints.
- Valid request and success response examples, with source IDs that can resolve.
- Validation rules, stable error codes/statuses, safe user messages and retryability.
- Timeout/deadline, overload and unavailable-dependency behavior.
- Correlation/submission IDs, idempotency and persistence semantics where applicable.
- Privacy constraints: what is retained, logged or sent externally.
- Test cases covering success, malformed input, unauthorized access and relevant failures.

Do not use guessed final limits: propose values, justify them and record team decisions. Align every schema and error name with the diagram and AI flows. Examples must use fictional data.
