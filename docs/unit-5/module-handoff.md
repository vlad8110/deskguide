# DeskGuide module assignments and integration handoff

These are Vlad's implementation assignments based on the [alpha preparation plan](alpha-preparation-plan.md). Members confirm availability, first deliverable and blockers with Vlad. Assignment does not record completed work or a member's acceptance. Use the [C4 interface contracts](https://github.com/vlad8110/deskguide/blob/bf6e11dcf420f042c3384d5ae3cb3494d9e0d257/docs/unit-3/interface-contracts.md) and [backlog implementation map](../backlog/implementation-map.md) when agreeing request/response shapes. The combined C4 design remains under peer review in [PR #15](https://github.com/vlad8110/deskguide/pull/15).

## Contributions and ownership

Keep a one-line purpose description in each source file. Use this handoff for module ownership, integration boundaries and acceptance checks. Git history records file authorship and dates; record meaningful completed work and its review evidence in [implementation contributions](../../contributions.md). Assigned ownership does not establish a completed contribution.

## Current starting point

The local foundation provides startup, SQLite schema initialization, controlled account management, C9 login/session/logout, reusable authorization helpers and a browser sign-in/workspace shell. The foundation tests use isolated fictional data.

The application does not yet implement the inquiry, retrieval, generation, evidence-validation, source-view, support, feedback or document-management product workflows. Existing storage tables and access helpers are integration points for that work.

## Existing files and where to connect

| Existing file | Responsibility | Integration work |
| --- | --- | --- |
| [app/__init__.py](../../app/__init__.py) | Vlad: app factory, configuration, sessions and request hooks | Register business blueprints in `create_app()`. Keep inquiry orchestration and persistence logic in dedicated service modules. Preserve session, CSRF and error hooks. |
| [app/auth.py](../../app/auth.py) | Vlad: C9 authentication; Hanlin consumes the API | Use `/v1/session/login-token` before login, `/v1/session` for session state and `/v1/session/logout` to sign out. Send same-origin cookies and `X-CSRF-Token` on state changes. |
| [app/access.py](../../app/access.py) | Vlad: identity, roles and ownership; David verifies | Business routes use `current_access()` and appropriate role/ownership guards. Pass the trusted context to internal services. Never accept a request-supplied customer scope as authority. |
| [app/accounts.py](../../app/accounts.py) | Vlad: local provisioning and permissions | Request fictional staff/customer fixtures from Vlad. Public UI must not create accounts or assign roles. Membership in the development team is separate from application permissions. |
| [app/db.py](../../app/db.py) | Vlad: connections, initialization and migrations | Services use `get_db()` and transactions. Coordinate schema changes before editing an initialized database. UI calls services through endpoints. |
| [app/clock.py](../../app/clock.py) | Vlad: shared time source | Use `now()` for the injectable auth/application clock and `timestamp()` for UTC API text; do not import authentication into persistence/account helpers. |
| [app/schema.sql](../../app/schema.sql) | Vlad coordinates; Collins uses source storage | Collins uses versioned documents/sections and grants; Vlad implements inquiry/support/receipt/feedback writes. Preserve foreign-key ownership and unique submission constraints. |
| [app/errors.py](../../app/errors.py) | Vlad: shared error envelope; Hanlin: display | Raise `ApiError` for agreed failures. UI uses the safe message, code and retry guidance; David verifies no private exception details escape. |
| [home.html](../../app/templates/home.html), [workspace.js](../../app/static/workspace.js), [workspace.css](../../app/static/workspace.css) | Hanlin: browser views and interactions | Extend the shell or introduce focused templates/assets for questions, results, exact source links, confirmed support, feedback and authorized staff views. |
| [tests/conftest.py](../../tests/conftest.py) | David: fixtures; Vlad maintains startup hooks | Extend temporary stores, controlled time and deterministic dependency substitutes. Keep test-only probe routes out of the product app. |
| [foundation tests](../../tests/test_foundation.py), [session tests](../../tests/test_sessions.py), [access tests](../../tests/test_access.py), [authentication hardening](../../tests/test_auth_hardening.py) | David: regressions; module owners fix findings | Retain existing checks and add tests against each real endpoint, not only helper probes. |
| [.env.example](../../.env.example), [runtime dependencies](../../requirements.txt), [development dependencies](../../requirements-dev.txt) | Vlad: shared setup; Collins: provider needs; David: CI | Agree dependency changes, document variable names and keep real credentials in ignored configuration. Reproduce setup without a teammate's private environment. |

## Shared setup and maintenance

Keep session expiry, CSRF, revocation and per-request authorization checks intact when adding endpoints. Health checks and static assets must not count as user activity. Use the documented [cleanup, proxy and secure-profile settings](../foundation.md) rather than adding a second session policy. API error responses stay safe; server error logs retain exception traces and correlation IDs. Treat server logs as restricted operational data.

Coordinate schema migrations and additional dependencies with Vlad before changing shared setup. Collins proposes provider requirements without adding real keys to source; David verifies installation and regression execution with temporary data. [pytest.ini](../../pytest.ini) supplies test discovery/import paths and filters only the known Flask-Session deprecation. All other warnings remain visible.

Use `@require_roles(...)` and `@require_permission(...)` as route decorators. Service code calls `check_permission(...)` or `check_independent_authorizer(...)` and uses the returned trusted context. Add future schema steps through the [migration runner](../foundation.md#database-upgrades); keep version-1 bootstrap SQL intact after release. Health checks cover the library-managed HTTP-session table as well as the schema version.

## Vladimyr Merci — application, authorization and persistence

**Next deliverable:** the C1 inquiry coordinator behind `POST /v1/inquiries`.

1. Agree callable inputs/outputs with Collins and browser response examples with Hanlin using the current contracts. Use the existing `AccessContext`; preserve identity derived from the session.
2. Implement request validation, route selection, admission/deadline handling and inquiry metadata. A question request does not grant access to any customer record or source.
3. Connect authorized retrieval, C10 `prepare_evidence`, the ready expectation, generation and C10 `validate` in that order. A failed/unavailable precheck makes zero provider calls; rejected output returns the agreed controlled outcome.
4. Coordinate the C4/C5 support and C6 feedback backend with Hanlin: explicit customer confirmation, durable save, registered IDs, safe retry/receipt replay and authorized customer/assigned-agent lookup. Existing tables do not supply these behaviors automatically.
5. Register completed modules in `create_app()`, coordinate migrations and integrate the read-only C7 fictional customer-profile adapter if retained in the agreed alpha scope. Account-status checks use trusted customer scope and do not call retrieval or the provider.

**Completion evidence:** the real endpoint accepts the agreed request, denies invalid access, preserves the contract response/error structure and supports integration without exposing identity to the provider. Support acknowledgement follows a committed save; a same-ID retry does not duplicate a record.

## Hanlin Wang — browser workflows and interface compatibility

**Start here:** the existing template and static assets above, plus the documented C9 endpoints.

1. Retain working login/logout and add loading, expiry, access-denied, rate-limit and connection-error states. Browser code never selects a role or reads a provider credential.
2. Build question/result views for C1 and exact permitted source-section/version navigation for C2. Coordinate stable IDs with Collins. Show citations from returned, validated data.
3. Build C4 support preview/edit/cancel/confirm and retry/status states. Do not display a saved acknowledgement until the backend confirms durable saving.
4. Build the authorized C5 agent queue/request view and C6 feedback controls, including feedback for an inquiry without an answer. Coordinate backend ownership with Vlad before changing shared service files.
5. Build the bounded C8 document-admin view with Vlad/Collins. Document-admin access must not grant customer support or raw-feedback access.

**First handoff:** request/response examples and visible screen states for a supported question, unsupported question, dependency failure and confirmed support request. Fixtures can support UI development while endpoints are being built.

**Completion evidence:** browser controls use real endpoints, source links open the correct authorized version/section, error states are understandable, and customer/agent/admin paths retain server enforcement. Fixture-only screens remain development scaffolding until connected.

## Collins Amponsah — sources, retrieval, provider and C10 checks

**Start here:** the versioned source/grant tables, `current_access()` and the C2/C3/C10 contracts. Agree source-service interfaces with Vlad before connecting the inquiry coordinator.

1. Supply the bounded fictional corpus with stable source, section and version IDs, plus the 20 labeled evaluation questions and their exact evidence. David independently reviews the fixtures.
2. Implement authorized retrieval and exact source lookup. Filter permitted content using the trusted context before building any provider payload.
3. Implement C10 evidence preparation and post-generation validation against the reviewed manifest. Share the prepared expectation and validation outcome shape with Vlad.
4. Implement the C3 adapter with the selected provider/model and agreed timeout/failure behavior. It receives only permitted question/passages and agreed generation metadata, without `AccessContext`, customer-database fields or session details.
5. Coordinate configuration/dependency additions with Vlad. Supply supported, unsupported, unavailable-evidence and provider-timeout/quota/configuration cases to Hanlin and David. Automatic second-provider failover remains outside the selected B11 scope.

**First handoff:** reviewed corpus/ID manifest, callable service shapes and deterministic response fixtures for integration. Then supply one permitted working real-provider example and controlled failure outcomes.

**Completion evidence:** answers cite the exact permitted source sections/versions; unavailable or failed prechecks make zero provider calls; rejected output follows the controlled outcome; credentials are absent from repository files and browser requests.

## David Warren — verification, fixture review and CI

**Start here:** `tests/conftest.py` and the existing test modules, including migration and browser-response regressions. The current helper probes exercise reusable guards; add coverage for real business endpoints as they arrive.

1. Independently review Collins's fictional corpus, labels and evidence manifest before recording answer-evaluation results.
2. Extend meaningful tests for supported answers, denied source/customer access, zero-call prechecks, invalid citations, provider failures, support confirmation, duplicate-save replay and inquiry-owned feedback.
3. Review the prepared [project checks workflow](../../.github/workflows/checks.yml) with Vlad: it installs `requirements-dev.txt` and runs Ruff lint/format checks, pytest and Node browser-response tests. Verify its hosted run after publication and extend startup/integration checks as real modules arrive. Use deterministic provider substitutes and fictional configuration.
4. Reproduce startup from a clean checkout, review installation/usage instructions and record actual defects, fixes and residual technical debt with the responsible member.
5. Record actual-provider alpha evidence separately from mock-based CI, and coordinate B12 evaluation/B15 readiness. Local SQLite success is not proof of measured 10,000-customer capacity.

**First handoff:** reviewed fixture findings, added endpoint/security cases and a pipeline change ready for human review.

**Completion evidence:** reproducible test results and pipeline run links after publication, actionable findings, verified fixes and an independently repeatable demonstration. Review assignments and proposed dates remain in the [alpha plan](alpha-preparation-plan.md).

## Planned module locations

The following names are proposed locations, not existing implementations. Agree names before parallel edits and keep each member's changes focused.

| Planned location | Lead and boundary |
| --- | --- |
| `app/inquiries.py` | Vlad: C1 coordinator and its public route; calls Collins's internal services. |
| `app/retrieval.py` | Collins: C2 authorized retrieval; coordinate exact source-view routing with Vlad/Hanlin. |
| `app/generation.py` | Collins: C3 provider adapter with no identity/context payload. |
| `app/validation.py` | Collins: C10 preparation/validation; David supplies independent fixture review. |
| `app/support.py` | Vlad: C4/C5 backend; Hanlin: browser workflow; David: ownership/state/retry tests. |
| `app/feedback.py` | Vlad: C6 ownership/persistence; Hanlin: controls; coordinate reviewed-improvement scope with Collins/David. |
| `app/documents.py` | Vlad coordinates C8 backend; Hanlin: admin UI; Collins: stable source-version behavior. |
| `app/customer_profile.py` | Vlad: C7 fictional read-only adapter if retained in alpha scope; Hanlin: account-status view. |
| Additional `tests/test_*.py` | David coordinates endpoint/integration regressions with each module owner. |
| `.github/workflows/` | David with Vlad: the initial checks workflow is included; verify its actual runs in the pull request checks. |

## How a module is handed over

Provide the changed files, backlog/contract IDs, callable or endpoint shapes, reproducible setup/test commands, actual outcomes and any blocker or remaining limitation. Coordinate shared schema/contract changes with Vlad before editing. Submit related work through the agreed branch and peer-review process; reconcile shared review sources before updating repository snapshots.
