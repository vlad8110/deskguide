ALTER TABLE feedback RENAME TO legacy_feedback;

CREATE TABLE feedback (
    feedback_id TEXT PRIMARY KEY,
    inquiry_id TEXT NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    rating TEXT CHECK (rating IN ('helpful', 'not_helpful')),
    category TEXT CHECK (rating IS NULL OR category IS NULL OR (
        rating = 'not_helpful' AND category IN (
            'incorrect', 'incomplete', 'wrong_source', 'unclear',
            'too_much_escalation', 'fallback_unhelpful', 'other'
        )
    )),
    comment TEXT CHECK (rating IS NULL OR length(comment) <= 500),
    created_at INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending_review'
        CHECK ((state = 'legacy' AND rating IS NULL)
            OR (state = 'pending_review' AND rating IS NOT NULL)),
    FOREIGN KEY (inquiry_id, customer_id)
        REFERENCES inquiries(inquiry_id, customer_id) ON DELETE CASCADE
);

-- Legacy rows had categories but no rating. Keep them without inferring one.
INSERT INTO feedback (feedback_id, inquiry_id, customer_id, category, comment, created_at, state)
SELECT feedback_id, inquiry_id, customer_id, category, comment, created_at, 'legacy'
FROM legacy_feedback;

DROP TABLE legacy_feedback;

CREATE UNIQUE INDEX idx_feedback_one_rated_per_inquiry ON feedback(inquiry_id)
    WHERE rating IS NOT NULL;
