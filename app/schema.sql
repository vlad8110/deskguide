-- Version-1 SQLite schema and integrity constraints.

-- Local alpha schema. HTTP session records are managed by Flask-Session.
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    account_status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'administrator')),
    customer_id TEXT REFERENCES customers(customer_id) ON DELETE RESTRICT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    auth_version INTEGER NOT NULL DEFAULT 1 CHECK (auth_version > 0),
    created_at INTEGER NOT NULL,
    CHECK ((role = 'customer' AND customer_id IS NOT NULL)
        OR (role != 'customer' AND customer_id IS NULL))
);

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    permission TEXT NOT NULL CHECK (permission IN ('reviewer', 'release_authorizer')),
    PRIMARY KEY (user_id, permission)
);

-- Revocation survives a stale in-flight HTTP session write after logout.
CREATE TABLE IF NOT EXISTS active_sessions (
    session_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    auth_version INTEGER NOT NULL,
    issued_at INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0, 1)),
    CHECK (expires_at > issued_at)
);
CREATE INDEX IF NOT EXISTS idx_active_sessions_user ON active_sessions(user_id, revoked);

CREATE TABLE IF NOT EXISTS documents (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'retired')),
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS document_versions (
    source_id TEXT NOT NULL REFERENCES documents(source_id) ON DELETE RESTRICT,
    source_version INTEGER NOT NULL CHECK (source_version > 0),
    content_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (source_id, source_version)
);

CREATE TABLE IF NOT EXISTS document_sections (
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    section_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (source_id, source_version, section_id),
    FOREIGN KEY (source_id, source_version)
        REFERENCES document_versions(source_id, source_version) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS document_role_grants (
    source_id TEXT NOT NULL REFERENCES documents(source_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'administrator')),
    PRIMARY KEY (source_id, role)
);

CREATE TABLE IF NOT EXISTS document_customer_grants (
    source_id TEXT NOT NULL REFERENCES documents(source_id) ON DELETE CASCADE,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, customer_id)
);

-- Ordinary question/answer text is intentionally absent from inquiry metadata.
CREATE TABLE IF NOT EXISTS inquiries (
    inquiry_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    route TEXT NOT NULL CHECK (route IN ('ai', 'account_status', 'human_requested')),
    outcome TEXT,
    answer_id TEXT,
    configuration_version TEXT,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    UNIQUE (inquiry_id, customer_id)
);

CREATE TABLE IF NOT EXISTS submission_registrations (
    submission_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    operation TEXT NOT NULL CHECK (operation IN ('escalation', 'reply')),
    parent_request_id TEXT REFERENCES support_requests(request_id) ON DELETE RESTRICT,
    state TEXT NOT NULL DEFAULT 'unused'
        CHECK (state IN ('unused', 'completed', 'expired')),
    registered_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK (expires_at > registered_at),
    CHECK ((operation = 'reply' AND parent_request_id IS NOT NULL)
        OR (operation = 'escalation' AND parent_request_id IS NULL)),
    UNIQUE (submission_id, customer_id),
    FOREIGN KEY (parent_request_id, customer_id)
        REFERENCES support_requests(request_id, customer_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS support_requests (
    request_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL UNIQUE
        REFERENCES submission_registrations(submission_id) ON DELETE RESTRICT,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 5000),
    reason TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'assigned', 'in_review', 'waiting_for_customer', 'resolved')),
    assigned_agent_id TEXT REFERENCES users(user_id) ON DELETE RESTRICT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    CHECK ((state = 'queued' AND assigned_agent_id IS NULL)
        OR (state != 'queued' AND assigned_agent_id IS NOT NULL)),
    UNIQUE (request_id, customer_id),
    FOREIGN KEY (submission_id, customer_id)
        REFERENCES submission_registrations(submission_id, customer_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS support_replies (
    reply_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES support_requests(request_id) ON DELETE RESTRICT,
    submission_id TEXT NOT NULL UNIQUE
        REFERENCES submission_registrations(submission_id) ON DELETE RESTRICT,
    author_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 5000),
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS submission_receipts (
    submission_id TEXT PRIMARY KEY
        REFERENCES submission_registrations(submission_id) ON DELETE RESTRICT,
    request_id TEXT NOT NULL REFERENCES support_requests(request_id) ON DELETE RESTRICT,
    payload_fingerprint TEXT NOT NULL,
    committed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    inquiry_id TEXT NOT NULL REFERENCES inquiries(inquiry_id) ON DELETE CASCADE,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    category TEXT NOT NULL,
    comment TEXT,
    created_at INTEGER NOT NULL,
    UNIQUE (inquiry_id, customer_id, category),
    FOREIGN KEY (inquiry_id, customer_id)
        REFERENCES inquiries(inquiry_id, customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS login_attempts (
    bucket TEXT PRIMARY KEY,
    failures INTEGER NOT NULL CHECK (failures >= 0),
    reset_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inquiries_owner ON inquiries(customer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_support_owner ON support_requests(customer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_support_agent ON support_requests(assigned_agent_id, state);
CREATE INDEX IF NOT EXISTS idx_unused_submissions
    ON submission_registrations(customer_id, state, expires_at);
CREATE INDEX IF NOT EXISTS idx_login_expiry ON login_attempts(reset_at);
