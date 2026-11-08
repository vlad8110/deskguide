-- Agent messages and content-free transition events follow request retention.
ALTER TABLE support_replies ADD COLUMN request_version INTEGER;
CREATE TABLE support_agent_messages (
    message_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES support_requests(request_id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('message_to_customer', 'resolution_note')),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
    created_at INTEGER NOT NULL,
    request_version INTEGER NOT NULL CHECK (request_version > 1),
    UNIQUE (request_id, request_version)
);
CREATE INDEX idx_agent_messages_request ON support_agent_messages(request_id, created_at);
CREATE TABLE support_state_events (
    event_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES support_requests(request_id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    actor_role TEXT NOT NULL CHECK (actor_role IN ('agent', 'customer')),
    operation TEXT NOT NULL CHECK (operation IN ('claim', 'transition', 'customer_reply')),
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 1),
    reason_given INTEGER NOT NULL DEFAULT 0 CHECK (reason_given IN (0, 1)),
    correlation_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (request_id, version)
);
CREATE INDEX idx_state_events_request ON support_state_events(request_id, created_at);
CREATE INDEX idx_support_queue ON support_requests(state, created_at, request_id);
CREATE INDEX idx_support_assigned ON support_requests(assigned_agent_id, created_at, request_id);
