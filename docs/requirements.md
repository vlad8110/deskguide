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
