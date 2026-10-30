# Proposed requirements

Instructor approval is pending. These acceptance criteria are for team review.

- A supported question produces an answer with valid source references to fictional document passages.
- A question without supporting evidence produces an explicit limitation and a support-request option.
- Submitted support requests can be saved and read back.
- Employees cannot invoke administrator document-management or support-review endpoints.
- API timeouts and quota errors preserve the question and offer the fallback.
- Feedback can be saved and reviewed.
- A documented evaluation set covers supported questions, unsupported questions, misleading evidence, source links, permissions, persistence, and failures.

Proposed components: browser interface → Flask endpoints → retrieval → answer generation → citation validation or support fallback. SQLite stores metadata, feedback, and requests. The exact component contracts and acceptance targets need team agreement.

## Current backlog and production design

The text above is the historical prototype proposal. Use the [refined backlog](backlog/refined-eight-week-backlog-v2.md), [four-week sprint](backlog/refined-four-week-sprint-backlog.md) and [implementation map](backlog/implementation-map.md) for acceptance criteria and current evidence. The Unit 3 production design adds 10,000-customer capacity, customer-data integration, agent escalation and reviewed improvement flow; see [Unit 3 requirements](unit-3/assignment-requirements.md).
