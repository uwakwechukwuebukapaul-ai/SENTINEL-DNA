CREATE TABLE IF NOT EXISTS billing_provider_events (
    provider_event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tenant_id TEXT,
    processed_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_billing_provider_events_tenant ON billing_provider_events(tenant_id, processed_at);
