# DeskGuide

DeskGuide is Team 4’s CMSC 495 capstone project: a browser application for customer-support questions using fictional workplace documents and links to supporting sources.

**Status:** Flask/SQLite foundation, [C1 inquiry coordinator](docs/inquiry-coordinator.md), [C4 support backend](docs/support-backend.md) and [C5 agent workflow](docs/agent-support.md) implemented. The customer question and support screens, citation lookup and customer feedback submission are available. Live AI/retrieval adapters and the feedback review queue remain integration work. Run `migrate-db` on existing databases to apply schema version 4 before using this revision. Run `cleanup-inquiries` periodically to remove expired inquiry metadata and linked feedback.

## Team

| Member | Role | Responsibility |
| --- | --- | --- |
| Vladimyr Merci | Lead Architect | System diagrams and architecture coordination |
| Hanlin Wang | Interface Designer | API specifications and component interfaces |
| Collins Amponsah | Integration Lead | AI flow and integration strategy |
| David Warren | Solutions Engineer | Testing, security validation, and integration troubleshooting |

## Proposed scope

- Questions answered from retrieved fictional document passages with source links.
- An explicit insufficient-evidence response and saved support-request fallback.
- Separate customer, agent and document-administrator permissions enforced by the server.
- Feedback, answer-support tests, access checks, and API failure handling.

Real company integrations, password resets, autonomous actions, and custom model training are outside the prototype scope.

## Proposed tools

Python and Flask; HTML, CSS, and JavaScript; SQLite; local document retrieval; one AI answer-generation provider selected after evaluation. No AI provider or paid service has been activated.

## Design baseline

The Unit 3 combined design is under review in [PR #15](https://github.com/vlad8110/deskguide/pull/15). Application integration uses the [C4 interface contracts](https://github.com/vlad8110/deskguide/blob/bf6e11dcf420f042c3384d5ae3cb3494d9e0d257/docs/unit-3/interface-contracts.md); the review documents remain on their separate branch. Vlad coordinates implementation through the [module handoff](docs/unit-5/module-handoff.md), with completed work recorded in [contributions](contributions.md).

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
- Use Cursor or another editor. You do not need a separate SQL server: Python includes SQLite support. No AI-provider account or API key is required to run the current sign-in foundation.

On Windows, use **PowerShell** for the Windows commands below. On macOS/Linux, use a terminal. Run one command at a time from the project folder.

### 2. Download the implementation branch

Open the [Flask foundation branch](https://github.com/vlad8110/deskguide/tree/feat/flask-foundation) and select `feat/flask-foundation` when cloning or switching branches. The branch is under team review; `main` may contain an earlier project version.

**Recommended for team collaboration — GitHub Desktop:**

1. On the repository page, choose **Code → Open with GitHub Desktop** and select a local destination.
2. In GitHub Desktop, use **Current Branch** to select the shared implementation branch. A clone initially opens the default branch, which may contain an earlier project version.
3. Open that local repository folder in Cursor. In Cursor, open a terminal at the repository root: the folder containing `README.md`, `requirements-dev.txt` and `app/`.

**Terminal alternative:**

```sh
git clone --branch feat/flask-foundation https://github.com/vlad8110/deskguide.git
cd deskguide
```

If Vlad shares a different branch name, use that name after `--branch`.

**Download-only alternative:** select the same implementation branch on GitHub, choose **Code → Download ZIP**, extract the archive, then open the extracted folder in Cursor. ZIP downloads can run the app, but do not include Git history or a connected clone for normal team collaboration.

Before installing, confirm that `app/__init__.py`, `app/schema.sql`, `.env.example` and `requirements-dev.txt` exist in the folder. If any are missing, check the branch and folder location.

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

This enables the local HTTP preview on localhost/loopback. Keep the AI settings empty for the current foundation. `.env`, `.venv` and database files are ignored by Git; do not upload them or copy another person's environment/database.

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

### 6. Run the foundation checks

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
| Missing `app/` files or Flask cannot import `app` | Select the implementation branch and run commands from the folder containing `app/` and this README. |
| Setup is incomplete or tables are missing | Use `init-db` for a new database; coordinate `migrate-db` and a verified backup for an existing older version. A newer database needs matching application code. |
| `Accounts already exist` during `seed-demo` | Skip seeding. Sign in with existing credentials or use `create-user`/`set-password`; retain the existing database. |
| Password rejected during account creation | Choose 12–128 characters and confirm the same value at the hidden prompt. |
| Login fails | Use an account created on this computer and its chosen password. Vlad's local accounts do not travel with the repository. |
| Login succeeds but the session is not retained | Confirm `.env` contains `DESKGUIDE_LOCAL_HTTP=1`, restart the server, and use its localhost/loopback URL. |
| Too many sign-in attempts | Wait for the displayed retry interval before trying again. |

When reporting a setup problem, include your operating system, Python version, selected branch, command used and the error message. Omit passwords, `.env` contents and API keys. Use the [module handoff](docs/unit-5/module-handoff.md) for your assigned implementation and completion checks.

Setup references: [GitHub cloning](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository), [Python virtual environments](https://docs.python.org/3.13/library/venv.html), [Flask installation](https://flask.palletsprojects.com/en/stable/installation/).

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

## Backlog and implementation tracking

Use the [backlog hub](docs/backlog/README.md), [refined four-week sprint](docs/backlog/refined-four-week-sprint-backlog.md) and [implementation map](docs/backlog/implementation-map.md) to connect the original/refined tasks to current work. The [module handoff](docs/unit-5/module-handoff.md) identifies the next implementation deliverables and owners.
