# DeskGuide

DeskGuide is Team 4’s CMSC 495 capstone project: a browser application for customer-support questions using fictional workplace documents and links to supporting sources.

**Unit 5 alpha:** Use the [tested revision `c34f414`](https://github.com/vlad8110/deskguide/tree/c34f414b2d235e32b50cdb094cd702fc7c1f8d6d) for grading. Start with [Run locally](#run-locally), then follow [Run the AI demo](#run-the-ai-demo) if you have an authorized Cohere evaluation key. [Project checks passed](https://github.com/vlad8110/deskguide/actions/runs/44179913048) for this revision. The [November 17 Render deployment](https://dashboard.render.com/web/srv-dbplie0u01pc73dnfrt0/deploys/dep-dbuceig8v5cc738mh3jg) recorded `c34f414` going live. See the [local Cohere acceptance record](#local-cohere-acceptance-record) for the live provider results.

The alpha includes the customer question and support screens, [inquiry coordination](docs/inquiry-coordinator.md), [support persistence](docs/support-backend.md), the [agent workflow](docs/agent-support.md), version-pinned citations, and customer feedback submission. The feedback review queue remains future work. Run `migrate-db` on an existing database to apply schema version 4. The Render Gunicorn worker purges expired inquiry metadata and linked feedback at startup and daily. For manual use, run `cleanup-inquiries`.

## Team

| Member | Role | Responsibility |
| --- | --- | --- |
| Vladimyr Merci | Lead Architect | System diagrams and architecture coordination |
| Hanlin Wang | Interface Designer | API specifications and component interfaces |
| Collins Amponsah | Integration Lead | AI flow and integration strategy |
| David Warren | Solutions Engineer | Testing, security validation, and integration troubleshooting |

## Alpha scope

- Questions answered from retrieved fictional document passages with source links.
- An explicit insufficient-evidence response and saved support-request fallback.
- Separate customer, agent and document-administrator permissions enforced by the server.
- Feedback, answer-support tests, access checks, and API failure handling.

Real company integrations, password resets, autonomous actions, and custom model training are outside the prototype scope.

## Tools

Python, Flask, HTML, CSS, JavaScript, and SQLite. The alpha retrieves passages from three pinned fictional guides and uses Cohere for supported questions when configured.

## Design baseline

The [Unit 3 design hub](docs/unit-3/README.md) links to the combined architecture review. Application integration uses the [Unit 3 interface contracts](docs/unit-3/interface-contracts.md). Vlad coordinates implementation through the [module handoff](docs/unit-5/module-handoff.md), with completed work recorded in [contributions](contributions.md).

Vlad's [architecture first draft](docs/unit-3/architecture-first-draft/README.md) is available for team review, with the editable Google Doc, shared draw.io diagram, PNG preview and Markdown copies. PDFs are reserved for final submission.

## Start here

1. Read [the collaboration guide](CONTRIBUTING.md).
2. Review [requirements](docs/requirements.md), [the weekly plan](docs/weekly-plan.md), and [free resource options](docs/resources.md).
3. Use Issues to agree on work and acceptance criteria. Vlad coordinates tasks; technical roles remain in place throughout the course.
4. Implement small changes on branches and open pull requests for peer review.

The [local Python development guide](docs/local-development.md) explains the environment and Cursor setup. The [foundation guide](docs/foundation.md) covers the schema, accounts, session API and remaining module handoffs. `requirements.txt` lists runtime dependencies; `requirements-dev.txt` adds pytest and Ruff.

Before a pull request, run Ruff lint/format checks and pytest using the [development guide](docs/local-development.md#run-project-tests). The [checks workflow](.github/workflows/checks.yml) also runs offline browser-response tests on Node 24. For an existing database after a schema release, follow [database upgrades](docs/foundation.md#database-upgrades) rather than deleting local data.

## Run locally

Each teammate runs a separate copy on their own computer. The code comes from GitHub; your Python environment, `.env`, SQLite database and test accounts are created locally. Accounts created on Vlad's computer are not included in the download.

### 1. Install the prerequisites

- Install **Python 3.13** from [Python downloads](https://www.python.org/downloads/). The development baseline in `.python-version` is 3.13.18. Use the standard Python 3.13 build for your operating system.
- Install [GitHub Desktop](https://desktop.github.com/download/) for cloning, branch selection and team changes, or install [Git](https://git-scm.com/downloads) for the terminal option.
- Use Cursor or another editor. You do not need a separate SQL server: Python includes SQLite support. No provider account or API key is needed for sign-in, the support workflow, or offline tests.

On Windows, use **PowerShell** for the Windows commands below. On macOS/Linux, use a terminal. Run one command at a time from the project folder.

### 2. Check out the tested alpha

Clone the repository. The instructions below pin the exact Unit 5 revision used for grading and live evaluation.

```sh
git clone https://github.com/vlad8110/deskguide.git
cd deskguide
git checkout --detach c34f414b2d235e32b50cdb094cd702fc7c1f8d6d
```

For a download without Git, use the [source ZIP for this commit](https://github.com/vlad8110/deskguide/archive/c34f414b2d235e32b50cdb094cd702fc7c1f8d6d.zip). Run the commands below from the extracted folder. For ongoing development, use the `main` branch and create a feature branch for changes.

### 3. Create your Python environment and local settings

Use the block for your operating system. These commands call the environment's Python directly, so activating the environment or changing PowerShell script permissions is unnecessary.

**macOS/Linux:**

```sh
python3.13 --version
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
```

**Windows PowerShell:**

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

The version check should show Python 3.13.x. If `python3.13` or `py -3.13` is unavailable, finish installing Python 3.13 and reopen the terminal before continuing.

Copy `.env.example` only on first setup. If `.env` already exists, keep your settings and skip the copy command. The template leaves local HTTP disabled. For your local preview, open `.env` and uncomment or add:

```dotenv
DESKGUIDE_LOCAL_HTTP=1
```

This enables the local HTTP preview on localhost/loopback. For support-only use, leave the AI settings empty. `.env`, `.venv` and database files are ignored by Git; do not upload them or copy another person's environment/database.

### 4. Initialize your database and create test accounts

**macOS/Linux:**

```sh
.venv/bin/python -m flask --app app init-db
.venv/bin/python -m flask --app app seed-demo
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m flask --app app init-db
.\.venv\Scripts\python.exe -m flask --app app seed-demo
```

At the hidden password prompt, choose a local demonstration password containing **12–128 characters**, then enter it again to confirm. No characters appear while typing. There is no built-in default password. The four accounts below use the password you choose on your computer:

| Username | Application role | Test purpose |
| --- | --- | --- |
| `customer-demo` | Customer | First fictional customer scope |
| `customer-two` | Customer | Separate customer scope for isolation checks |
| `agent-demo` | Agent | Agent-role testing as support endpoints are implemented |
| `admin-demo` | Document administrator | Document-admin role testing, without support-content access |

The database is created at `instance/deskguide.sqlite3`. `init-db` can be rerun without dropping existing records. `seed-demo` only works when both the customer and user stores are empty; it refuses to overwrite existing accounts. On an existing setup, skip seeding and use your existing login or the management commands below.

**Optional: create a first-name customer login.** Replace `yourname` with your first name in both commands, including the customer ID. Keep the ID unique on your local database. Enter a 12–128-character password at the hidden prompt.

macOS/Linux:

```sh
.venv/bin/python -m flask --app app create-customer team-yourname --name "Fictional team test customer"
.venv/bin/python -m flask --app app create-user yourname --role customer --customer-id team-yourname
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m flask --app app create-customer team-yourname --name "Fictional team test customer"
.\.venv\Scripts\python.exe -m flask --app app create-user yourname --role customer --customer-id team-yourname
```

Use usernames of 3–64 letters, digits, dots, dashes or underscores, beginning with a letter or digit. Creating an account does not give it staff permissions. See the [foundation guide](docs/foundation.md#account-management) for controlled agent/admin provisioning, access changes and password changes.

### 5. Start DeskGuide and sign in

Run the appropriate command from the repository root:

**macOS/Linux:**

```sh
.venv/bin/python -m flask --app app --no-debug run --host 127.0.0.1 --port 5055 --no-reload
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m flask --app app --no-debug run --host 127.0.0.1 --port 5055 --no-reload
```

Leave that terminal running. Open [http://127.0.0.1:5055/](http://127.0.0.1:5055/) in a browser on the same computer and sign in with a seeded username or the account you created. Use your locally chosen password.

Successful login shows `Welcome, <username>`, the application role and a **Sign out** button. Customers can ask a question, submit feedback, and open support requests. Agents can work their support queue. You can also open [the health check](http://127.0.0.1:5055/health), which should return JSON containing `"status": "ok"` after database initialization.

Press **Ctrl+C** in the server terminal to stop it. To return later, open the repository folder and rerun only the start command; keep your `.env` and existing database/accounts. The server uses `--no-reload`, so restart it after Python code changes. `127.0.0.1` refers to the computer opening the link; it is not a shared team website.

### 6. Run the offline checks

Use a second terminal at the repository root, or stop the server first. An activated environment is not required.

**macOS/Linux:**

```sh
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Tests create isolated temporary databases and fictional accounts. They do not use your local login/database. A successful run finishes with passing tests; review any failures before handing over changes.

### Troubleshooting

| Symptom | What to check |
| --- | --- |
| `127.0.0.1 refused to connect` | Start the Flask command and leave its terminal open. Check that the browser uses the same port. |
| Port 5055 is already in use | Use the already-running DeskGuide instance, or change `--port 5055` to `--port 5056` and open `http://127.0.0.1:5056/`. |
| `No module named flask` or `pytest` | Install `requirements-dev.txt` using the `.venv` Python command for your operating system. Use that same interpreter to start/test. |
| Missing `app/` files or Flask cannot import `app` | Check out the tested alpha and run the commands from the folder containing `app/` and this README. |
| Setup is incomplete or tables are missing | Use `init-db` for a new database; coordinate `migrate-db` and a verified backup for an existing older version. A newer database needs matching application code. |
| `Accounts already exist` during `seed-demo` | Skip seeding. Sign in with existing credentials or use `create-user`/`set-password`; retain the existing database. |
| Password rejected during account creation | Choose 12–128 characters and confirm the same value at the hidden prompt. |
| Login fails | Use an account created on this computer and its chosen password. Vlad's local accounts do not travel with the repository. |
| Login succeeds but the session is not retained | Confirm `.env` contains `DESKGUIDE_LOCAL_HTTP=1`, restart the server, and use its localhost/loopback URL. |
| Too many sign-in attempts | Wait for the displayed retry interval before trying again. |

When reporting a setup problem, include your operating system, Python version, selected branch, command used and the error message. Omit passwords, `.env` contents and API keys. Use the [module handoff](docs/unit-5/module-handoff.md) for your assigned implementation and completion checks.

Setup references: [GitHub cloning](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository), [Python virtual environments](https://docs.python.org/3.13/library/venv.html), [Flask installation](https://flask.palletsprojects.com/en/stable/installation/).

## Run the AI demo

Start from a fresh local demo database with the fictional accounts from step 4. Follow the [release checklist](sample_documents/corpus_v1/UNIT5-RELEASE-CHECKLIST.md) if using an existing database. It describes the exact guide versions and how to audit existing grants before import.

Import the pinned release using the virtual environment’s Python. This grants the customer role access to DOC-001 v1, DOC-002 v1, and DOC-003 v3.

```sh
.venv/bin/python -m flask --app app import-citation-release sample_documents/corpus_v1/release.json --grant-customer DOC-001 --grant-customer DOC-002 --grant-customer DOC-003
```

On Windows, use `.\.venv\Scripts\python.exe` in place of `.venv/bin/python`. Set these entries in the ignored local `.env`:

```dotenv
DESKGUIDE_AI_PROVIDER=cohere
DESKGUIDE_CITATION_RELEASE=sample_documents/corpus_v1/release.json
COHERE_API_KEY=
```

Enter your authorized evaluation key on the last line in your local file. Keep it out of Git and browser settings. Restart Flask from the repository root and sign in as `customer-demo`. In **Ask a question**, submit:

- **How do I set up the Campus VPN profile?** The answer’s citation should open DOC-003, section s2, version 3.
- **Which printer driver should I install?** DeskGuide should offer a support request. The offline regression tests use a simulated provider and assert zero calls for this question. The live acceptance run measured the outgoing calls separately.

[The recorded release decision](https://github.com/vlad8110/deskguide/issues/4#issuecomment-6961363565) lists the exact guide and manifest hashes.

## Local Cohere acceptance record

On November 17, 2026, between 4:21 and 4:24 p.m. Eastern, the team ran the cases below through a local Flask test client with fictional accounts and disposable SQLite. The combined PR #33 and #34 source tree matched [alpha revision `c34f414`](https://github.com/vlad8110/deskguide/tree/c34f414b2d235e32b50cdb094cd702fc7c1f8d6d). SQLite contained exactly the three pinned guide versions and three customer-role grants, with no individual grants. The live configuration used Cohere Chat v2, model `command-r7b-12-2024`, and a server-side evaluation key.

| Case | Observed result | Outgoing Cohere calls |
| --- | --- | ---: |
| Q08 Campus VPN profile | Answer returned. Opening the citation for DOC-003, section s2, version 3 returned HTTP 200. | 1 successful |
| Q18 Printer driver | DeskGuide offered a support request. | 0 |

The test counted calls at the provider transport. To repeat it, use the pinned revision and [AI demo setup](#run-the-ai-demo) with disposable data, submit the two cases, and record provider transport counts for each. [The GitHub project checks](https://github.com/vlad8110/deskguide/actions/runs/44179913048) ran offline. The [Cohere regression tests](tests/test_cohere_services.py) use a simulated provider. The live results above apply to the local run. Render deployment and health were verified separately.

## Where work belongs

| Location | Contents |
| --- | --- |
| GitHub | Code, tests, interface definitions, diagrams, technical notes, and tasks |
| Google Docs and Drive | Editable Unit 3 Google Doc/draw.io review sources, submission exports and course artifacts kept outside the public repository |
| Email | Optional notification only; decisions and coordination are recorded in GitHub |

## Folder layout

```text
app/                Flask application, schema, access controls and local sign-in
tests/              Automated foundation and authorization tests
docs/               Requirements and planning
sample_documents/   Fictional source material only
.github/            Project-check workflow, issue and pull request templates
```

Keep API keys, `.env` files, real workplace records, personal information, and live databases out of Git. Use `.env.example` only for placeholders.

Work from a local clone using GitHub Desktop or your editor. Review local changes before committing and pushing; see the [collaboration guide](CONTRIBUTING.md). Shared Google Doc and diagram edits must be reconciled explicitly before updating their repository snapshots.

## Backlog and implementation tracking

Use the [backlog hub](docs/backlog/README.md), [refined four-week sprint](docs/backlog/refined-four-week-sprint-backlog.md) and [implementation map](docs/backlog/implementation-map.md) to connect the original/refined tasks to current work. The [module handoff](docs/unit-5/module-handoff.md) identifies the next implementation deliverables and owners.
