# Flask SQLite and access control foundation

The local foundation implements application startup, schema initialization, controlled account management and C9 sessions/access controls. The browser provides working sign-in/sign-out and a signed-in workspace. The question, retrieval, AI, support and feedback product flows remain separate implementation work.

See the [module assignments and integration handoff](unit-5/module-handoff.md) for each teammate's starting files, responsibilities, next deliverable and completion evidence. Source files have one-line purpose descriptions; [implementation contributions](../contributions.md) records completed work and review evidence.

## Startup

On first setup, copy `.env.example` to an ignored `.env` file and uncomment `DESKGUIDE_LOCAL_HTTP=1` for the loopback preview. Preserve an existing `.env`. Configure this before running initialization or other management commands; startup outside local/testing mode requires `SECRET_KEY`.

From the repository folder:

```sh
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m flask --app app init-db
python -m flask --app app seed-demo
DESKGUIDE_LOCAL_HTTP=1 python -m flask --app app --no-debug run --host 127.0.0.1 --port 5055 --no-reload
```

Open [the local workspace](http://127.0.0.1:5055). `seed-demo` asks for a password at a hidden prompt, confirms it, and creates two fictional customers plus `customer-demo`, `customer-two`, `agent-demo` and `admin-demo` accounts. These local demonstration accounts use the password you choose. No default password or account credential is stored in source code or a plaintext file. The command refuses to overwrite an existing account store.

For an existing database with provisioned accounts, skip `seed-demo` and sign in with an existing account. Use the account-management commands below for additional users or access changes; rerunning setup does not recreate named team accounts.

The app defaults to Secure, HttpOnly, SameSite=Lax cookies. `DESKGUIDE_LOCAL_HTTP=1` explicitly enables cookies for this loopback HTTP demonstration and restricts accepted hosts to localhost/loopback. An HTTPS deployment must leave local HTTP disabled, provide a persistent `SECRET_KEY` through its private configuration and use a configured application server. The Flask development server is the local preview. Only explicit local mode and isolated tests may generate a temporary key.

### Reverse-proxy deployment

Direct/local requests ignore forwarded headers by default. Behind a trusted reverse proxy, set `DESKGUIDE_PROXY_X_FOR` to the number of trusted proxies supplying `X-Forwarded-For` and `DESKGUIDE_PROXY_X_PROTO` to the number supplying `X-Forwarded-Proto`. For one trusted proxy that supplies both, set each to `1`. These counts are independent and must match the actual deployment; invalid or negative counts stop startup.

The proxy must replace untrusted incoming forwarded headers, and the application server must be reachable only through the trusted proxies. Forwarded host, port and prefix headers are not trusted. This keeps login address limits tied to the original client without letting direct clients choose a rate-limit address. Verify the real proxy/TLS configuration before deploying.

`GET /health` returns 200 when the application schema version matches the code and Flask-Session's `http_sessions` table has its required columns. Missing/incomplete session storage or an outdated schema returns 503. `init-db` initializes a fresh database through all registered versions without dropping existing records; an initialized older database requires the explicit upgrade command below.

Readiness requests ignore cookies before session loading. A stale browser cookie therefore cannot prevent the storage check or turn missing session storage into a session-loading error. The check does not clear the browser's login cookie.

## Account management

Accounts are provisioned through management commands, with no public sign-up or client-selected role:

```sh
python -m flask --app app create-customer example-customer --name "Fictional Customer"
python -m flask --app app create-user example-user --role customer --customer-id example-customer
python -m flask --app app create-user example-agent --role agent
python -m flask --app app set-password example-user
python -m flask --app app set-access example-agent --role agent --permission reviewer
```

Password commands prompt without echoing input or accepting a password in the command line. Passwords must be 12–128 characters and are stored as Werkzeug scrypt hashes. Customer accounts require an existing fictional customer mapping. Staff accounts cannot carry customer scope. Review/release permissions are explicit, independent of staff role, and cannot be granted to customer accounts through these commands. `set-access` replaces the permission set; omitting permissions removes them.

Role, permission and password changes revoke every existing session for that account. Logout revokes the current session only. Account management belongs to the trusted local operator; it is not exposed through an HTTP administration endpoint.

## Session API

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/session/login-token` | Creates a pre-login CSRF token in a server-side anonymous session; the token is valid for ten minutes. |
| `POST /v1/session/login` | JSON containing only username/password, plus X-CSRF-Token; verifies credentials and rotates the opaque session ID. Returns the server-derived role, contract_version and correlation_id. |
| `GET /v1/session` | C9 response: role, absolute expires_at, idle_expires_at, csrf_token, contract_version and correlation_id. No customer scope or session credential is returned. |
| `POST /v1/session/logout` | Requires an authenticated session and its X-CSRF-Token; invalidates that session and returns 204. Replaying the invalid session returns 401. |

Authenticated application activity is saved at most once per minute per session; the HTTP session/cookie refreshes with that heartbeat instead of every request. The 30-minute idle deadline uses the latest saved activity, so it can expire less than a minute earlier than an unsaved request would suggest. `idle_expires_at` reports that saved deadline accurately. The eight-hour absolute deadline never slides. Health checks and static assets do not renew activity.

Flask-Session stores opaque sessions in SQLite through its SQLAlchemy backend; the application does not use Flask’s client-side identity cookies. Only JSON is decoded from the fresh session store, without legacy pickle fallback.

An independent database session registry retains revocation until absolute expiry. It is the authority for issued/last-seen times; the HTTP-session payload carries only identity, authorization version, CSRF and permanence state. This prevents an old in-flight session write from restoring authorization after logout. Every protected request checks the live account state and authorization version, even if it arrives through another app instance sharing the same database. Shared time and UTC formatting helpers live in `app/clock.py`.

The login endpoint limits failed attempts by normalized account name and source address using database-backed counters. Unknown accounts and bad passwords use the same safe error. Correlation IDs are generated by the server; client-provided identity, role, scope and correlation headers do not grant authority. API errors use the 0.3.3 envelope and do not expose raw SQL, passwords or stack traces.

Login limits are rechecked after password verification inside a short write transaction, so overlapping attempts cannot bypass the configured threshold. Password hashing runs outside that write lock.

Expired library sessions, including abandoned anonymous login-token sessions, have automatic request-based cleanup enabled at an average of 100 requests. Occasional maintenance writes are separate from authenticated activity refreshes. For explicit local maintenance, or regular scheduled maintenance in a deployment, run:

```sh
python -m flask --app app cleanup-auth
```

`cleanup-auth` removes expired HTTP sessions, expired registry records and login counters while preserving live sessions and unexpired revocation tombstones. Library expiry uses UTC wall time; registry/counter expiry uses the application's auth clock. In a deployment, schedule this command regularly, for example every five minutes, with the same private environment and database path as the app. Request-based cleanup provides a fallback for the local prototype; no operating-system scheduler is installed by setup.

Werkzeug HTTP errors retain their numeric status and protocol headers. In particular, 401 maps to `UNAUTHENTICATED`, 403 to `FORBIDDEN`, 415 to `UNSUPPORTED_MEDIA_TYPE` and 429 to `RATE_LIMITED`. Missing routes and disallowed methods return 404/405 before endpoint-specific authentication/CSRF checks; known protected state-changing endpoints still enforce both.

## Schema and module handoffs

The explicit [schema](../app/schema.sql) enables foreign keys on application connections, constraints and ownership indexes. Local database files and sessions are under the ignored `instance` directory.

Application services use raw `sqlite3`; Flask-Session uses SQLAlchemy against the same database file. These are separate connections and transactions, so a service transaction does not also commit session storage. Both have a five-second SQLite timeout. Flask-Session owns `http_sessions`; application migrations own the remaining tables and schema version.

### Database upgrades

Version 1 retains the planned source, inquiry, support, reply, receipt and feedback tables for the agreed design and ownership tests. Their presence does not implement the corresponding product endpoints. [app/db.py](../app/db.py) now supplies a small forward-only migration runner, so future changes do not require resetting the database.

Before upgrading an existing installation, stop application writers and make a verified backup. With the same private environment/database settings as the app, run:

```sh
python -m flask --app app migrate-db
```

For a schema change, add the next numbered SQL file under `app/migrations/` and append its path to `MIGRATIONS` in `app/db.py`. The tuple order defines version numbers and `SCHEMA_VERSION`; `schema.sql` is the version-1 bootstrap and must remain unchanged once released. Add upgrade/preservation and rollback tests before accepting a migration. No additional version is registered until it has a real schema change.

The runner holds a SQLite write lock, rechecks the version and applies every pending step in one transaction. A failure rolls back both schema/data changes and the version. Migration files cannot issue transaction-control statements or PRAGMAs; the runner owns those. A database newer than the code is rejected, and a current database is a no-op. `init-db` never silently upgrades an initialized older database. Examples of these paths are in [migration tests](../tests/test_migrations.py).

| Tables | Purpose |
| --- | --- |
| customers, users, user_permissions | Fictional customer mapping, credentials, role and explicit staff permissions |
| http_sessions, active_sessions, login_attempts | Library session storage, revocation/absolute/idle state and failed-login limits |
| documents, document_versions, document_sections | Stable source identities and versioned section content |
| document_role_grants, document_customer_grants | Explicit permitted source scopes; no automatic broad grant |
| inquiries | Minimal inquiry metadata without ordinary question/answer transcript columns |
| submission_registrations, support_requests, support_replies, submission_receipts | Registered intents, durable support/replies and uniqueness constraints |
| feedback | Inquiry-owned feedback, including inquiries with no answer |

Foreign keys bind a request’s customer to the registered submission and feedback’s customer to the inquiry. The unique submission key prevents a second request for the same registration. These constraints support the future services; they do not implement the complete C4/C5 state machine, receipt replay, expiry/three-ID admission, retention cleanup or endpoints.

| Module | Integration point |
| --- | --- |
| Hanlin’s interfaces | Use the C9 endpoints with same-origin cookies and X-CSRF-Token. Keep the browser from selecting identity or role. |
| Protected Flask routes | Use `current_access()` and `require_roles()` from app/access.py. Request state changes automatically require a session-bound CSRF token. |
| Support service | `get_owned_support_request(context, request_id)` exposes full content only to the owning customer or assigned agent. Build the separate authorized unassigned queue using its bounded summary contract. Document admins do not inherit support access. |
| Review/release services | Use `@require_permission(...)` for views and `check_permission(...)` inside services. `check_independent_authorizer(author_id)` rejects self-authorization with 403 `FORBIDDEN`; services also enforce exact evaluated version, independent review and rollback requirements. |
| Collins’s retrieval/provider work | Use the versioned source tables and trusted access context internally. The provider adapter must receive only the permitted generation payload, without access context or customer fields. C10 is not implemented by this foundation. |
| David’s verification | Extend the isolated pytest suite for each real endpoint. The test-only role/content probes are registered in tests/conftest.py and are not product endpoints. |

## Validation and limits

Run `python -m pytest -q`. Tests use temporary databases and fictional accounts. They verify startup, non-destructive initialization, database ownership/uniqueness constraints, hashed provisioning, server-side sessions, cookie flags, role and ownership denial, CSRF, login limits, idle/absolute expiry, session rotation, multi-instance access and revocation, and password changes.

Run `python -m ruff check .` and `python -m ruff format --check .` for Python lint/style checks, and `node --test tests/browser.test.cjs` with Node 24 for browser-response regressions. The browser tests substitute fetch/DOM behavior and include non-JSON proxy failures; they do not claim a full browser or integrated alpha demonstration.

The [project checks workflow](../.github/workflows/checks.yml) runs on pull requests and pushes to main. It installs pinned development dependencies and runs lint, formatting, pytest and browser-response tests without provider credentials. Hosted results are recorded in the pull request checks. SQLite and the local Flask server are the bounded alpha foundation; production deployment and measured 10,000-customer capacity remain separate work.

References: [Flask application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/), [Flask testing](https://flask.palletsprojects.com/en/stable/testing/), [Flask-Session configuration](https://flask-session.readthedocs.io/en/latest/config.html), [trusted proxy configuration](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/), [Werkzeug password hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash).
