"""Additive billing persistence schema; does not alter canonical identity tables."""
VERSION = 5
DESCRIPTION = "Commercial billing records"
def upgrade(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS billing_customers (tenant_id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_customer_id TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS billing_transactions (transaction_reference TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, provider TEXT NOT NULL, provider_transaction_id TEXT UNIQUE, plan_id TEXT NOT NULL, status TEXT NOT NULL, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS billing_subscriptions (tenant_id TEXT PRIMARY KEY, provider TEXT NOT NULL, plan_id TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS billing_events (event_id TEXT PRIMARY KEY, provider TEXT NOT NULL, event_type TEXT NOT NULL, transaction_reference TEXT, received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
