CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memberships (
    membership_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id), role TEXT NOT NULL,
    created_at TEXT NOT NULL, UNIQUE(user_id, organization_id)
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL, revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS usage_events (
    event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT, event_type TEXT NOT NULL,
    quantity INTEGER NOT NULL, resource_type TEXT, resource_id TEXT, metadata TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_type_time ON usage_events(tenant_id, event_type, created_at);
