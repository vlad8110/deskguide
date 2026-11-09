# C2 retrieval adapter test plan

Use isolated fictional fixtures: two customer scopes, an allowed
source, a restricted source, and two versions of one section. Use a
fake clock for deadlines and inject failures into the policy and store.

| Case | Expected result |
| --- | --- |
| A restricted result would outrank an allowed result with top_k=1 | The allowed result gets the slot. |
| No permitted passages match | Return an empty tuple and a valid index version. |
| An authorized caller opens an eligible exact reference | Return the requested source, section, and version. |
| The requested version is missing but another version exists | Return None; never substitute another version. |
| A grant is revoked after retrieval | Exact lookup rechecks permission and returns None. |
| A source is retired | Exclude it from retrieval; exact lookup returns None. |
| The policy or store fails | Raise a failure rather than returning an empty success. |
| The deadline expires | Raise a timeout; do not retry or return partial results. |

Grant combination and approved-version selection remain open decisions.
The fixture policy supplies explicit decisions for each test. PR #21's
corpus stays pending review and is not used by these tests.
