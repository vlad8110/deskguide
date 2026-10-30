# Initial eight-week backlog — source snapshot

Imported October 29, 2026 from the [shared source](https://docs.google.com/document/d/15HHjKox_H5YgZ6iClIg69MwCaTMhyaZK/edit). Wording below is preserved; Markdown headings/spacing replace Word styling. Revision comments and tracked formatting are not reproduced. Historical status statements are source text, not a current completion audit. Use [current integration](implementation-map.md) for scope changes and implementation status.

Unit 2 Initial Eight Week Backlog

AI-generated initial baseline • October 22, 2026 • Pending team evaluation

I generated this initial backlog from our DeskGuide proposal for us to review together. This is the starting point for the Backlog Challenge, not our refined sprint backlog or a record of work already completed. We will preserve this version, identify three tasks that are out of scope or technically risky, rewrite them, and prepare our agreed Weeks 1–4 Sprint Backlog separately.

Planning assumptions

We have four team members. The eight weeks below are proposed project planning stages, not confirmed course dates or a claim that eight new weeks remain. We will map the refined plan to the remaining course calendar and actual LEO deadlines. Application development depends on instructor approval. Our initial scope uses fictional documents, a browser interface, Flask, SQLite, document retrieval, one model API, source links, feedback, saved support requests, and employee/administrator permissions.

Backlog notation

F means functional behavior; N means a non-functional quality constraint; D means a data requirement; T means a technical or planning task. Effort is an initial estimate in person-hours for each item, including its stated checks. Estimates and lead assignments are proposals, not commitments. Each item needs peer review. Targets below are proposed acceptance criteria, not measured performance or guarantees.

## Week 1 Scope and evaluation foundation

### B01 Agree on core stories, exclusions, and the backlog.

Type: T  |  Suggested lead: Vlad  |  Estimated effort: 3–4 person-hours

Dependencies: None.

Proposed acceptance: Team-reviewed scope lists the question flow, sources, feedback, support requests, and permissions; instructor approval is recorded before implementation.

### B02 Prepare a bounded fictional document collection and evaluation cases.

Type: D  |  Suggested lead: Collins with David  |  Estimated effort: 4–6 person-hours

Dependencies: B01.

Proposed acceptance: Prepare 8–12 documents with stable IDs and sections, plus 20 questions: 12 supported, 4 unsupported, and 4 ambiguous or misleading. Record expected supporting passages or fallback behavior.

### B03 Sketch employee and administrator workflows and component boundaries.

Type: T  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 3–5 person-hours

Dependencies: B01.

Proposed acceptance: Review wireframes and a component diagram covering questions, citations, requests, feedback, and document administration.

Initial weekly estimate: 10–15 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 2 Interfaces storage and provider selection

### B04 Define request/response contracts and error cases.

Type: T  |  Suggested lead: Hanlin  |  Estimated effort: 4–6 person-hours

Dependencies: B02, B03.

Proposed acceptance: Agree on schemas for questions, answers, source IDs, feedback, and support requests, including validation and unauthorized/error responses.

### B05 Compare two free model API options.

Type: T  |  Suggested lead: Collins with David  |  Estimated effort: 4–6 person-hours

Dependencies: B02.

Proposed acceptance: Use the same small evaluation subset, record answer support, latency, limits, and permitted use, and recommend one option without assuming trial access covers public production.

### B06 Create the Flask skeleton and SQLite schema.

Type: F/D  |  Suggested lead: Vlad  |  Estimated effort: 4–6 person-hours

Dependencies: B01, B04, approval.

Proposed acceptance: A clean local setup runs; migrations or schema setup create document metadata, role, feedback, and support-request structures; tests use temporary data.

Initial weekly estimate: 12–18 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 3 Retrieval and employee interface

### B07 Implement passage retrieval from fictional documents.

Type: F/D  |  Suggested lead: Collins  |  Estimated effort: 5–7 person-hours

Dependencies: B02, B06.

Proposed acceptance: Return ranked passage IDs with resolvable source sections; at least 10 of 12 supported evaluation questions retrieve an expected passage within the top three.

### B08 Build the employee question and result views.

Type: F  |  Suggested lead: Hanlin  |  Estimated effort: 4–6 person-hours

Dependencies: B04, B06.

Proposed acceptance: Validate empty/oversized input, show loading and error states, and display source links using agreed response fixtures while AI integration is pending.

### B09 Implement demo sign-in and employee/administrator authorization.

Type: F/N  |  Suggested lead: Vlad with David  |  Estimated effort: 5–7 person-hours

Dependencies: B04, B06.

Proposed acceptance: Use controlled demo accounts; employee requests to every administrator endpoint are denied in automated tests; no real identity-provider integration.

Initial weekly estimate: 14–20 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 4 AI answer vertical slice

### B10 AI user story: As an employee, I want an answer based on relevant fictional documents with source links so I can verify the guidance.

Type: F  |  Suggested lead: Collins  |  Estimated effort: 6–8 person-hours

Dependencies: B05, B07, B08.

Proposed acceptance: Provide retrieved passages to the selected model, return source IDs, and render links to actual document sections. Supported and unsupported paths can be demonstrated end to end.

### B11 Offer the support-request fallback and preserve the question.

Type: F  |  Suggested lead: Hanlin with Collins  |  Estimated effort: 4–6 person-hours

Dependencies: B06, B08, B10.

Proposed acceptance: Unsupported evidence or an API failure displays a clear limitation and a prefilled request form; submitted requests are saved and read back.

### B12 Evaluate initial answer support and response time.

Type: N  |  Suggested lead: David  |  Estimated effort: 4–6 person-hours

Dependencies: B02, B10, B11.

Proposed acceptance: On the fixed 20-question set, manually score citation support and fallback behavior; propose at least 10 of 12 supported answers fully supported and all 4 unsupported questions routed to fallback. Target at most 15 seconds for 9 of 10 sequential demo requests; record environment and all failures.

Initial weekly estimate: 14–20 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 5 Alpha completion and review

### B13 Add feedback and administrator request review.

Type: F  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 5–7 person-hours

Dependencies: B06, B09, B11.

Proposed acceptance: Feedback is saved with its answer reference; administrators list saved requests while employees cannot access the review endpoint.

### B14 Add administrator management of the bounded document collection.

Type: F/D  |  Suggested lead: Hanlin with Collins  |  Estimated effort: 4–6 person-hours

Dependencies: B07, B09.

Proposed acceptance: Administrator can replace a fictional source and rebuild its retrieval representation; source IDs remain consistent and invalid input is rejected.

### B15 Package the alpha and conduct peer review.

Type: T  |  Suggested lead: David with team  |  Estimated effort: 4–6 person-hours

Dependencies: B10–B14.

Proposed acceptance: Record setup instructions, demonstrated features, known defects, review findings, and prioritized fixes. Align submission with the actual course milestone.

Initial weekly estimate: 13–19 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 6 Security reliability and a stretch experiment

### B16 Test authorization, hostile document instructions, and provider failures.

Type: N  |  Suggested lead: David with Collins  |  Estimated effort: 5–7 person-hours

Dependencies: B09–B15.

Proposed acceptance: Cover role denial, malformed inputs, instructions embedded in source text, timeouts, and quota errors; verify credentials remain server-side and questions survive failures.

### B17 Add a second AI provider with automatic failover.

Type: N  |  Suggested lead: Collins with David  |  Estimated effort: 8–12 person-hours

Dependencies: B05, B12.

Proposed acceptance: A simulated primary-provider failure triggers one secondary attempt without duplicate support requests; both providers pass the same output contract and citation checks. This initial item introduces additional provider setup and test effort for team scrutiny.

### B18 Prioritize and resolve the most consequential alpha defects.

Type: T  |  Suggested lead: Vlad with team  |  Estimated effort: 3–5 person-hours

Dependencies: B15, B16.

Proposed acceptance: Document severity and dependency decisions; re-run relevant checks after fixes and record residual limitations.

Initial weekly estimate: 16–24 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 7 Documentation and stakeholder preparation

### B19 Prepare the user guide, architecture notes, and demonstration script.

Type: T  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 4–6 person-hours

Dependencies: B15, B18.

Proposed acceptance: Explain setup, roles, citations, limitations, and support fallback; diagrams and contracts match the current implementation.

### B20 Deploy a continuously available public demonstration with 25 concurrent sessions.

Type: N  |  Suggested lead: Vlad with David  |  Estimated effort: 8–12 person-hours

Dependencies: B15, B16.

Proposed acceptance: Configure persistent storage and protected administrator access; run a 25-session test and record uptime, errors, and costs. Free hosting capacity and public-demo requirements remain unverified initial assumptions.

### B21 Rehearse with fictional employee questions.

Type: T  |  Suggested lead: Team; David coordinates  |  Estimated effort: 3–5 person-hours

Dependencies: B19.

Proposed acceptance: Walk through a supported answer, unsupported question, denied administrator action, and provider failure; collect usability corrections.

Initial weekly estimate: 15–23 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 8 Final validation and portfolio

### B22 Run final regression and clean-setup validation.

Type: T/N  |  Suggested lead: David  |  Estimated effort: 4–6 person-hours

Dependencies: B18, B19, B21.

Proposed acceptance: A teammate follows documented setup; core functional, permission, persistence, and AI evidence checks are rerun; known failures are disclosed.

### B23 Assemble the final project portfolio and stakeholder presentation.

Type: T  |  Suggested lead: Vlad with team  |  Estimated effort: 5–7 person-hours

Dependencies: B19, B22.

Proposed acceptance: Package the agreed release, instructions, diagrams, test evidence, limitations, and presentation materials; each member prepares their individual component.

### B24 Obtain final agreement and submit the required deliverables.

Type: T  |  Suggested lead: Vlad coordinates  |  Estimated effort: 2–3 person-hours

Dependencies: B23.

Proposed acceptance: Confirm the required files and links, record team approval and submission confirmation, and retain a reproducible release snapshot.

Initial weekly estimate: 11–16 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

Suggested Division of Work for This Week

For our current Unit 2 discussion week, I suggest the following division of work. These are review responsibilities for the assignment, not instructions to implement the entire backlog this week. Please suggest changes before we finalize our team submission.

Vladimyr Merci Lead Architect and weekly coordinator

I will organize the initial backlog, collect everyone’s review, map the critical path and team capacity, and combine the refined Weeks 1–4 backlog. I will collect approval and coordinate the team post in LEO.

Hanlin Wang Interface Designer

Review user stories, browser workflows, API schemas, dependencies, and acceptance criteria. Identify one task that is too broad or risky and propose a narrower replacement; distinguish functional behavior from quality targets.

Collins Amponsah Integration Lead

Review retrieval, model API selection, source links, fallback, and data dependencies. Identify one risky or out-of-scope task and propose a feasible replacement with a clear integration boundary.

David Warren Solutions Engineer

Review test effort, permissions, accuracy and latency targets, hosting assumptions, and failure handling. Identify one risky task and propose a measurable, achievable replacement with validation steps.

What I need back from everyone

Please send your recommended task changes, why each change is needed, revised acceptance criteria, and estimated effort. We will select three distinct problem tasks, preserve their original wording, and document our rewrites and reasons in a separate refined version. We will also agree on data scope, accuracy targets, performance limits, and the dependency chain before posting.

Each of us must also complete the individual response to another team by evaluating its critical path against the assignment’s three-person-team scenario. Our own backlog uses our actual four-person roster. We will use the dates and time zone displayed in LEO rather than treating the planning-week labels as deadlines.
