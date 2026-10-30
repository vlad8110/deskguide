# Refined backlog Revision 2 — source snapshot

Imported October 29, 2026 from the [shared source](https://docs.google.com/document/d/1Am7vauy3Tc3SpDvp0t4IRULnu7jL9SdS/edit). Wording below is preserved; Markdown headings/spacing replace Word styling. Revision comments and tracked formatting are not reproduced. Historical status statements are source text, not a current completion audit. Use [current integration](implementation-map.md) for scope changes and implementation status.

Unit 2 Refined Backlog

Revision 2 • October 25, 2026 • Collins, Hanlin, and David reviews incorporated • Awaiting team approval

I have incorporated Collins’s, Hanlin’s, and David’s recommendations into this review version. All revised text remains red. Comments preserve the original baseline wording and, where revised again, the wording from Revision 1. Our three proposed task rewrites are B17, B20, and B12. B11 now specifies duplicate prevention, and Weeks 2–4 include earlier contract, authorization, source-verification, and integration checks. We still need team approval and the final Weeks 1–4 discussion post.

Planning assumptions

We have four team members. The eight weeks below are proposed project planning stages, not confirmed course dates or a claim that eight new weeks remain. We will map the refined plan to the remaining course calendar and actual LEO deadlines. Application development depends on instructor approval. Our initial scope uses fictional documents, a browser interface, Flask, SQLite, document retrieval, one model API, source links, feedback, saved support requests, and employee/administrator permissions.

Backlog notation

F means functional behavior; N means a non-functional quality constraint; D means a data requirement; T means a technical or planning task. Effort is an initial estimate in person-hours for each item, including its stated checks. Estimates and lead assignments are proposals, not commitments. Each item needs peer review. Targets below are proposed acceptance criteria, not measured performance or guarantees.

## Week 1 Scope and evaluation foundation

<a id="b01"></a>

### B01 Agree on core stories, exclusions, and the backlog.

Type: T  |  Suggested lead: Vlad  |  Estimated effort: 3–4 person-hours

Dependencies: None.

Proposed acceptance: Team-reviewed scope lists the question flow, sources, feedback, support requests, and permissions; instructor approval is recorded before implementation.

<a id="b02"></a>

### B02 Prepare a bounded fictional document collection and evaluation cases.

Type: D  |  Suggested lead: Collins with David  |  Estimated effort: 4–6 person-hours

Dependencies: B01.

Proposed acceptance: Prepare 8–12 documents with stable IDs and sections, plus 20 questions: 12 supported, 4 unsupported, and 4 ambiguous or misleading. Record expected supporting passages or fallback behavior.

<a id="b03"></a>

### B03 Sketch employee and administrator workflows and component boundaries.

Type: T  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 3–5 person-hours

Dependencies: B01.

Proposed acceptance: Review wireframes and a component diagram covering questions, citations, requests, feedback, and document administration.

Initial weekly estimate: 10–15 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 2 Interfaces storage and provider selection

<a id="b04"></a>

### B04 Define request/response contracts and error cases.

Type: T  |  Suggested lead: Hanlin  |  Estimated effort: 4–6 person-hours

Dependencies: B02, B03.

Proposed acceptance: Agree on schemas for questions, answers, source IDs, feedback, and support requests, including validation and unauthorized/error responses. In Week 2, define contract tests for valid, malformed, unauthorized, and provider-error responses using fixtures. Run these tests as each endpoint is implemented.

<a id="b05"></a>

### B05 Compare two free model API options.

Type: T  |  Suggested lead: Collins with David  |  Estimated effort: 4–6 person-hours

Dependencies: B02.

Proposed acceptance: Compare two free model API options using the same evaluation subset. Record answer support, model, usage restrictions, request count, environment, and end-to-end response times. Report the median, slowest response, and failures. Recommend one provider and propose a measured latency target and a configured timeout for team agreement before B12 acceptance testing. Do not assume trial access covers public production.

<a id="b06"></a>

### B06 Create the Flask skeleton and SQLite schema.

Type: F/D  |  Suggested lead: Vlad  |  Estimated effort: 4–6 person-hours

Dependencies: B01, B04, approval.

Proposed acceptance: A clean local setup runs; migrations or schema setup create document metadata, role, feedback, and support-request structures; tests use temporary data.

Initial weekly estimate: 12–18 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 3 Retrieval and employee interface

<a id="b07"></a>

### B07 Implement passage retrieval from fictional documents.

Type: F/D  |  Suggested lead: Collins  |  Estimated effort: 5–7 person-hours

Dependencies: B02, B06.

Proposed acceptance: Return ranked passage IDs with resolvable source sections; at least 10 of 12 supported evaluation questions retrieve an expected passage within the top three. In Week 3, test missing and invalid source IDs and verify that each displayed source link resolves to the expected fictional document section.

<a id="b08"></a>

### B08 Build the employee question and result views.

Type: F  |  Suggested lead: Hanlin  |  Estimated effort: 4–6 person-hours

Dependencies: B04, B06.

Proposed acceptance: Validate empty/oversized input, show loading and error states, and display source links using agreed response fixtures while AI integration is pending.

<a id="b09"></a>

### B09 Implement demo sign-in and employee/administrator authorization.

Type: F/N  |  Suggested lead: Vlad with David  |  Estimated effort: 5–7 person-hours

Dependencies: B04, B06.

Proposed acceptance: Use controlled demo accounts; employee requests to every administrator endpoint are denied in automated tests; no real identity-provider integration. Run role-allow and role-denial checks when each endpoint is introduced in Week 3; repeat them after integration changes.

Initial weekly estimate: 14–20 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 4 AI answer vertical slice

<a id="b10"></a>

### B10 AI user story: As an employee, I want an answer based on relevant fictional documents with source links so I can verify the guidance.

Type: F  |  Suggested lead: Collins  |  Estimated effort: 6–8 person-hours

Dependencies: B05, B07, B08.

Proposed acceptance: Provide retrieved passages to the selected model, return source IDs, and render links to actual document sections. Supported and unsupported paths can be demonstrated end to end.

<a id="b11"></a>

### B11 Offer the support-request fallback and handle failures from the selected AI provider.

Type: F  |  Suggested lead: Hanlin with Collins; David supports testing  |  Estimated effort: 5–7 person-hours, subject to team review

Dependencies: B06, B08, B10.

Proposed acceptance: Unsupported evidence displays a clear limitation and offers a support-request form. Simulated timeouts, quota errors, and service failures return a consistent controlled error response without an unsupported answer. Preserve the original question in the prefilled form. Assign a unique submission ID and enforce its uniqueness in SQLite; retries using the same ID return the existing request without creating another record. Disable submission while pending. Verify that repeated submissions with the same ID create one retrievable record and a separate intentional request receives a new ID. Keep credentials server-side and hide technical error details. Test these paths during Week 4 integration.

<a id="b12"></a>

### B12 Evaluate initial answer support and response time.

Type: N  |  Suggested lead: David  |  Estimated effort: 4–6 person-hours

Dependencies: B02, B10, B11.

Proposed acceptance: On the fixed 20-question set, manually score citation support and fallback behavior. Retain the proposed targets of at least 10 of 12 supported answers fully supported and all 4 unsupported questions routed to fallback. Measure end-to-end latency for 10 sequential demo requests; report every result, median, slowest response, environment, model, timeouts, and failures. Apply the team-agreed latency target and configured timeout established after B05 measurements; document the values before testing and report pass/fail. Requests exceeding the timeout must show a controlled message and support fallback. Verify source IDs, links, and supporting passages.

Revised weekly estimate: 15–21 person-hours across the team, including the consolidated B11 work. Confirm availability and allow for course work, reviews, and rework.

## Week 5 Alpha completion and review

<a id="b13"></a>

### B13 Add feedback and administrator request review.

Type: F  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 5–7 person-hours

Dependencies: B06, B09, B11.

Proposed acceptance: Feedback is saved with its answer reference; administrators list saved requests while employees cannot access the review endpoint.

<a id="b14"></a>

### B14 Add administrator management of the bounded document collection.

Type: F/D  |  Suggested lead: Hanlin with Collins  |  Estimated effort: 4–6 person-hours

Dependencies: B07, B09.

Proposed acceptance: Administrator can replace a fictional source and rebuild its retrieval representation; source IDs remain consistent and invalid input is rejected.

<a id="b15"></a>

### B15 Package the alpha and conduct peer review.

Type: T  |  Suggested lead: David with team  |  Estimated effort: 4–6 person-hours

Dependencies: B10–B14.

Proposed acceptance: Record setup instructions, demonstrated features, known defects, review findings, and prioritized fixes. Align submission with the actual course milestone.

Initial weekly estimate: 13–19 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 6 Security reliability and regression checks

<a id="b16"></a>

### B16 Test authorization and hostile document instructions and recheck provider-failure handling.

Type: N  |  Suggested lead: David with Collins  |  Estimated effort: 5–7 person-hours

Dependencies: B09–B15.

Proposed acceptance: Cover role denial, malformed inputs, and instructions embedded in source text. Re-run the Week 4 timeout, quota-error, service-failure, question-preservation, and single-save checks after later integration changes. Confirm credentials remain server-side and technical error details remain hidden. Reuse B11 tests rather than creating a separate implementation. Re-run the contract, input-validation, authorization, and source-verification checks introduced in Weeks 2–4; Week 6 is the broader security and regression review.

<a id="b17"></a>

### B17 Handle failures from the selected AI provider through a consistent error response and support-request fallback.

Type: F/N  |  Suggested lead: Collins with David  |  Estimated effort: 3–5 person-hours, included in B11; no additional Week 6 implementation effort

Dependencies: B05, B06, B08, B10. Implement with B11 in Week 4; regression checks continue under B16.

Proposed acceptance: Use the consolidated B11 criteria for controlled errors, no unsupported answer, a prefilled original question, a single retrievable request, and protected credentials and error details. B17 is retained here as a revision reference, not a separate implementation task. Automatic failover to a second provider is a deferred stretch goal.

<a id="b18"></a>

### B18 Prioritize and resolve the most consequential alpha defects.

Type: T  |  Suggested lead: Vlad with team  |  Estimated effort: 3–5 person-hours

Dependencies: B15, B16.

Proposed acceptance: Document severity and dependency decisions; re-run relevant checks after fixes and record residual limitations.

Revised weekly estimate: 8–12 person-hours across the team for B16 and B18. B17 implementation is included in Week 4 B11 and is not counted again here. Confirm available time before finalizing.

## Week 7 Documentation and stakeholder preparation

<a id="b19"></a>

### B19 Prepare the user guide, architecture notes, and demonstration script.

Type: T  |  Suggested lead: Hanlin with Vlad  |  Estimated effort: 4–6 person-hours

Dependencies: B15, B18.

Proposed acceptance: Explain setup, roles, citations, limitations, and support fallback; diagrams and contracts match the current implementation.

<a id="b20"></a>

### B20 Demonstrate DeskGuide from a clean local setup and provide a recorded walkthrough.

Type: T/N  |  Suggested lead: Vlad with David  |  Estimated effort: 4–6 person-hours, subject to team review

Dependencies: B15, B16.

Proposed acceptance: A teammate follows the documented setup on a clean local environment. Demonstrate a supported answer with working citations, unsupported-question fallback, a saved retrievable support request, denied administrator access for an employee, and a simulated provider failure. Record a walkthrough and retain the setup instructions and test results. Confirm that local/classroom delivery plus a recording satisfies course requirements before finalizing; if hosting is required, revise this item with verified resources. Public availability and 25-session load testing are deferred.

<a id="b21"></a>

### B21 Rehearse with fictional employee questions.

Type: T  |  Suggested lead: Team; David coordinates  |  Estimated effort: 3–5 person-hours

Dependencies: B19.

Proposed acceptance: Walk through a supported answer, unsupported question, denied administrator action, and provider failure; collect usability corrections.

Revised weekly estimate: 11–17 person-hours across the team. B20 is provisionally 4–6 hours; B19 and B21 are unchanged. Confirm availability and course delivery requirements before finalizing.

## Week 8 Final validation and portfolio

<a id="b22"></a>

### B22 Run final regression and clean-setup validation.

Type: T/N  |  Suggested lead: David  |  Estimated effort: 4–6 person-hours

Dependencies: B18, B19, B21.

Proposed acceptance: A teammate follows documented setup; core functional, permission, persistence, and AI evidence checks are rerun; known failures are disclosed.

<a id="b23"></a>

### B23 Assemble the final project portfolio and stakeholder presentation.

Type: T  |  Suggested lead: Vlad with team  |  Estimated effort: 5–7 person-hours

Dependencies: B19, B22.

Proposed acceptance: Package the agreed release, instructions, diagrams, test evidence, limitations, and presentation materials; each member prepares their individual component.

<a id="b24"></a>

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
