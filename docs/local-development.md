# Local Python development environment

The local environment uses Python 3.13.18, Flask 3.1.3, python-dotenv 1.2.4 and pytest 9.2.0. Flask-Session 0.8.0 and Flask-SQLAlchemy 3.1.1 manage server-side HTTP sessions using SQLAlchemy 2.1.8. Python's built-in `sqlite3` module provides application database access. An additional SQL server is not needed for the local SQLite prototype.

The Flask application, schema and C9 access/session foundation are implemented locally. See [startup and account setup](foundation.md) to initialize the database and sign in. Retrieval, provider integration and support/feedback business endpoints remain separate backlog work; no production-capacity result is established by this foundation.

Use the [module handoff](unit-5/module-handoff.md) to identify your starting files, integration contracts and completion checks before adding a feature.

## Work in Cursor

Open the repository folder in Cursor and use **Python: Select Interpreter** to select `.venv/bin/python`. The local workspace settings point to that interpreter and enable pytest under `tests/`. They are excluded from Git along with the virtual environment and local database files.

The local editor extensions provide Python editing, Pyright analysis, Python debugging and SQLite queries. **Python: Current File** is available in Run and Debug for Python files as they are added. The SQLite extension's **SQLite: New Query** and **SQLite: Open Database** commands can be used when a local database has been created.

## Start a terminal session

From the repository root:

```sh
source .venv/bin/activate
python --version
python -m flask --version
python -m pip check
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Use `python -m pip` from this environment when installing project packages. Run `deactivate` when finished. The system Python remains separate.

## Recreate the environment

On this Mac, Python is installed through Homebrew:

```sh
brew install python@3.13
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

`.python-version` records the expected Python version. On first setup, copy `.env.example` to an ignored `.env` file and uncomment `DESKGUIDE_LOCAL_HTTP=1` for the loopback preview before running management commands. Preserve an existing `.env`. The template leaves local HTTP disabled; outside local/testing mode startup requires `SECRET_KEY` and cookies remain secure. No provider has been selected.

For runtime dependencies only, install `requirements.txt`. SQLite is part of the Python installation; do not install an unrelated package named `sqlite3` from a package registry. Python may use a different SQLite version on another machine; record its actual version when testing.

The Homebrew SQLite command-line tool on this Mac is available at `/opt/homebrew/opt/sqlite/bin/sqlite3`. Use `sqlite3 --version` in a new Cursor terminal to check it. Database files belong under the ignored `instance/` directory once the application schema is agreed.

## Run project tests

```sh
python -m pytest tests
python -m ruff check .
python -m ruff format --check .
```

`pytest.ini` sets `testpaths = tests` and adds the repository root to Python's import path. To run from another directory, pass the repository path to its environment's Python:

```sh
"/path/to/deskguide/.venv/bin/python" -m pytest "/path/to/deskguide"
```

Only Flask-Session's known `datetime.utcnow()` deprecation is filtered. Other warnings remain visible; remove that narrow filter when the dependency stops emitting it.

The foundation tests cover startup, schema constraints, provisioning, login, CSRF, role/ownership denial, session renewal/expiration, revocation, password changes and shared-store behavior across app instances. The authentication-hardening tests also cover expired HTTP-session cleanup, heartbeat write frequency, proxy trust, secure startup and routing/error responses. They use temporary fictional data. Product workflows and production capacity require their own integration tests and evidence.

`pyproject.toml` configures Ruff for Python 3.13 with an 88-column formatter and lint checks for Python errors, unused imports and import ordering. Use `python -m ruff format .` to apply formatting before review. Node 24 is needed only for the offline browser-response tests (`node --test tests/browser.test.cjs`), not to start Flask. No npm packages are required.

The workflow in `.github/workflows/checks.yml` runs these checks on pull requests and main-branch pushes. Review its actual results in the pull request checks; local results do not establish a hosted pass.

## Local changes and publication

Review local edits before committing. A commit records changes on this computer; a push publishes committed changes to GitHub. Use a branch and pull request for peer review. Keep the virtual environment, `.env`, credentials, private data and local databases out of Git.

Reference: [Flask installation and virtual environments](https://flask.palletsprojects.com/en/stable/installation/).
