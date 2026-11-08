-- Persist reviewed support details and the result identity for reply replay.
ALTER TABLE support_requests ADD COLUMN note TEXT;
ALTER TABLE support_requests ADD COLUMN inquiry_id TEXT
    REFERENCES inquiries(inquiry_id) ON DELETE SET NULL;
ALTER TABLE submission_receipts ADD COLUMN reply_id TEXT
    REFERENCES support_replies(reply_id) ON DELETE RESTRICT;
CREATE UNIQUE INDEX idx_receipt_reply ON submission_receipts(reply_id)
    WHERE reply_id IS NOT NULL;
CREATE INDEX idx_support_created ON support_requests(customer_id, created_at);
