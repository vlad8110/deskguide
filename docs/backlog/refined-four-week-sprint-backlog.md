# Refined four-week sprint backlog

This is an exact text extract of planning Weeks 1–4 (B01–B12) from [Revision 2](refined-eight-week-backlog-v2.md), with Markdown formatting. It is not represented as a separately verified final LEO submission. The shared source still labels the revision as awaiting team approval. Planning-week labels are stages, not new calendar deadlines or a claim that these tasks are complete.

The stage effort ranges total **51–74 team person-hours** before additional production design work or contingency. Actual capacity and remaining work must be confirmed. Use the [Unit 3 schedule](../unit-3/week-3-delivery-schedule.md) for the current assignment dates.

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

Proposed acceptance: Agree on schemas for questions, answers, source IDs, feedback, and support requests, including validation and unauthorized/error responses. In Week 2, define contract tests for valid, malformed, unauthorized, and provider-error responses using fixtures. Run these tests as each endpoint is implemented.

### B05 Compare two free model API options.

Type: T  |  Suggested lead: Collins with David  |  Estimated effort: 4–6 person-hours

Dependencies: B02.

Proposed acceptance: Compare two free model API options using the same evaluation subset. Record answer support, model, usage restrictions, request count, environment, and end-to-end response times. Report the median, slowest response, and failures. Recommend one provider and propose a measured latency target and a configured timeout for team agreement before B12 acceptance testing. Do not assume trial access covers public production.

### B06 Create the Flask skeleton and SQLite schema.

Type: F/D  |  Suggested lead: Vlad  |  Estimated effort: 4–6 person-hours

Dependencies: B01, B04, approval.

Proposed acceptance: A clean local setup runs; migrations or schema setup create document metadata, role, feedback, and support-request structures; tests use temporary data.

Initial weekly estimate: 12–18 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 3 Retrieval and employee interface

### B07 Implement passage retrieval from fictional documents.

Type: F/D  |  Suggested lead: Collins  |  Estimated effort: 5–7 person-hours

Dependencies: B02, B06.

Proposed acceptance: Return ranked passage IDs with resolvable source sections; at least 10 of 12 supported evaluation questions retrieve an expected passage within the top three. In Week 3, test missing and invalid source IDs and verify that each displayed source link resolves to the expected fictional document section.

### B08 Build the employee question and result views.

Type: F  |  Suggested lead: Hanlin  |  Estimated effort: 4–6 person-hours

Dependencies: B04, B06.

Proposed acceptance: Validate empty/oversized input, show loading and error states, and display source links using agreed response fixtures while AI integration is pending.

### B09 Implement demo sign-in and employee/administrator authorization.

Type: F/N  |  Suggested lead: Vlad with David  |  Estimated effort: 5–7 person-hours

Dependencies: B04, B06.

Proposed acceptance: Use controlled demo accounts; employee requests to every administrator endpoint are denied in automated tests; no real identity-provider integration. Run role-allow and role-denial checks when each endpoint is introduced in Week 3; repeat them after integration changes.

Initial weekly estimate: 14–20 person-hours across the team. Check each person’s available time and include course work, reviews, and rework when refining.

## Week 4 AI answer vertical slice

### B10 AI user story: As an employee, I want an answer based on relevant fictional documents with source links so I can verify the guidance.

Type: F  |  Suggested lead: Collins  |  Estimated effort: 6–8 person-hours

Dependencies: B05, B07, B08.

Proposed acceptance: Provide retrieved passages to the selected model, return source IDs, and render links to actual document sections. Supported and unsupported paths can be demonstrated end to end.

### B11 Offer the support-request fallback and handle failures from the selected AI provider.

Type: F  |  Suggested lead: Hanlin with Collins; David supports testing  |  Estimated effort: 5–7 person-hours, subject to team review

Dependencies: B06, B08, B10.

Proposed acceptance: Unsupported evidence displays a clear limitation and offers a support-request form. Simulated timeouts, quota errors, and service failures return a consistent controlled error response without an unsupported answer. Preserve the original question in the prefilled form. Assign a unique submission ID and enforce its uniqueness in SQLite; retries using the same ID return the existing request without creating another record. Disable submission while pending. Verify that repeated submissions with the same ID create one retrievable record and a separate intentional request receives a new ID. Keep credentials server-side and hide technical error details. Test these paths during Week 4 integration.

### B12 Evaluate initial answer support and response time.

Type: N  |  Suggested lead: David  |  Estimated effort: 4–6 person-hours

Dependencies: B02, B10, B11.

Proposed acceptance: On the fixed 20-question set, manually score citation support and fallback behavior. Retain the proposed targets of at least 10 of 12 supported answers fully supported and all 4 unsupported questions routed to fallback. Measure end-to-end latency for 10 sequential demo requests; report every result, median, slowest response, environment, model, timeouts, and failures. Apply the team-agreed latency target and configured timeout established after B05 measurements; document the values before testing and report pass/fail. Requests exceeding the timeout must show a controlled message and support fallback. Verify source IDs, links, and supporting passages.

Revised weekly estimate: 15–21 person-hours across the team, including the consolidated B11 work. Confirm availability and allow for course work, reviews, and rework.

## Dependency sequence

B01 → B02/B03 → B04 → B06 → B07/B08/B09 → B10 → B11 → B12. B05 runs after B02 and must finish before B10; B12 also depends on B02. The source treats instructor approval as an implementation prerequisite. Confirm the actual longest path from estimates and capacity rather than assuming this dependency sequence is a measured schedule.

Preserve the B10 AI user story, B04 early contract tests, B07 source validation, B09 early authorization tests, B11 single-save/provider-failure behavior, and B12 measured latency/timeout agreement. B17 is consolidated into B11, not a second implementation task.
