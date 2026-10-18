# DeskGuide

DeskGuide is Team 4’s CMSC 495 capstone proposal: a browser application that answers employee onboarding and IT questions using fictional workplace documents and links to supporting sources.

**Status:** Planning. Instructor approval is required before application development. This repository contains the collaboration scaffold; there is no runnable application yet.

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
- Employee and administrator permissions enforced by the server.
- Feedback, answer-support tests, access checks, and API failure handling.

Real company integrations, password resets, autonomous actions, and custom model training are outside the prototype scope.

## Proposed tools

Python and Flask; HTML, CSS, and JavaScript; SQLite; local document retrieval; one AI answer-generation provider selected after evaluation. No AI provider or paid service has been activated.

## Start here

1. Read [the collaboration guide](CONTRIBUTING.md).
2. Review [requirements](docs/requirements.md), [the weekly plan](docs/weekly-plan.md), and [free resource options](docs/resources.md).
3. Use Issues to agree on work and acceptance criteria. Weekly coordinators organize tasks; technical roles remain in place throughout the course.
4. After instructor approval, implement small changes on branches and open pull requests for peer review.

Setup commands and test instructions will be added when implementation dependencies and the first runnable increment are agreed. `requirements.txt` is intentionally a planning placeholder.

## Where work belongs

| Location | Contents |
| --- | --- |
| GitHub | Code, tests, interface definitions, diagrams, technical notes, and tasks |
| Google Docs and Drive | Team editing, study guides, references, and final course documents |
| Email | Weekly updates, decisions, and submission confirmation |

## Folder layout

```text
app/                Application code after approval
tests/              Automated tests after approval
docs/               Requirements and planning
sample_documents/   Fictional source material only
.github/            Issue and pull request templates
```

Keep API keys, `.env` files, real workplace records, personal information, and live databases out of Git. Use `.env.example` only for placeholders.
