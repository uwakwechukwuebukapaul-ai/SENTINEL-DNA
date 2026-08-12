CREATE TABLE IF NOT EXISTS billing_plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    billing_interval TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    entitlements TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS billing_customers (
    customer_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    provider_customer_id TEXT,
    billing_email TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS billing_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL UNIQUE,
    plan_id TEXT NOT NULL REFERENCES billing_plans(plan_id),
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_subscription_id TEXT,
    current_period_start TEXT NOT NULL,
    current_period_end TEXT NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscription_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subscription_id TEXT,
    event_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(tenant_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subscription_id TEXT,
    status TEXT NOT NULL,
    amount_due_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_invoice_id TEXT,
    idempotency_key TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tenant ON billing_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscription_events_tenant_time ON subscription_events(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_time ON invoices(tenant_id, created_at);
