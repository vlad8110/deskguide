# Working together

## Access

This repository is currently public. All current teammates have accepted collaborator write access as of October 29, 2026. Send Vlad your GitHub username so the correct account can be invited. Accept the invitation while signed into that account, then use **Code → Open with GitHub Desktop** or clone the repository from GitHub Desktop. An invitation has not been sent merely because this guide exists.

## Small reviewed changes

1. Open an Issue describing the work and acceptance criteria. Agree on the owner and course week.
2. Pull the latest `main` and create a short branch such as `docs/api-contract` or `feature/question-form`.
3. Commit only related files. Check the diff for credentials and private data.
4. Push the branch and open a pull request linked to the Issue.
5. Ask one teammate to review. Resolve comments and run the checks relevant to the change.
6. Merge reviewed, working changes into `main`; delete the finished branch.

One peer review is our workflow agreement. Whether GitHub can enforce it depends on the account plan and repository settings.

## Weekly updates

Use GitHub Issues, Markdown documents and pull requests as the single coordination location. Report completed work, blockers and next steps in the relevant issue. See [Unit 3](docs/unit-3/README.md) for current owners and milestones. Vlad remains coordinator unless he explicitly delegates a temporary handoff in GitHub. Record current assignment decisions in `docs/unit-3/decisions.md`; preserve earlier decisions as history.

The coordinator reviews the weekly requirements early, helps divide tasks, collects updates, organizes the final review, and confirms who submits agreed-upon team work. Individual quizzes and critiques remain each member’s responsibility.

## Local work and shared review sources

Use a local clone for repository work. GitHub Desktop provides the Changes and History views, commits and explicit push controls. Fetch the current remote state before starting, review local changes and reconcile others' work before publishing.

Vlad's workflow is to make and review changes on his computer first. A commit records changes locally; a push publishes committed changes to GitHub. Commit or publish his work only when he explicitly requests that action. Do not enable automatic publishing.

For the [Unit 3 architecture draft](docs/unit-3/architecture-first-draft/README.md), the Google Doc and shared draw.io file are the editable review sources. Repository Markdown, draw.io and PNG files are snapshots. Reconcile shared edits and refresh the local snapshots before committing a revision. Use PNG previews during review; create the PDF for final submission.

## Development approval

Planning can proceed now. Application development begins only after instructor approval of the pitch. Do not add a paid service without team agreement. Do not commit working credentials, in this public repository.
