"""Additive durable crypto quotes and payment intents."""
VERSION = 6
DESCRIPTION = "Durable provider-neutral crypto quotes and payment intents"
def upgrade(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS crypto_quotes (quote_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, plan_id TEXT NOT NULL, fiat_amount_minor INTEGER NOT NULL, fiat_currency TEXT NOT NULL, asset TEXT NOT NULL, network TEXT NOT NULL, rate TEXT NOT NULL, crypto_amount TEXT NOT NULL, rate_source TEXT NOT NULL, rate_timestamp TEXT NOT NULL, expires_at TEXT NOT NULL, rounding_policy TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS crypto_payment_intents (payment_intent_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, transaction_reference TEXT NOT NULL UNIQUE, quote_id TEXT NOT NULL UNIQUE, plan_id TEXT NOT NULL, asset TEXT NOT NULL, network TEXT NOT NULL, provider TEXT NOT NULL, provider_reference TEXT UNIQUE, destination TEXT NOT NULL, status TEXT NOT NULL, idempotency_key TEXT NOT NULL, payment_expires_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, idempotency_key));
    CREATE INDEX IF NOT EXISTS idx_crypto_quotes_tenant ON crypto_quotes(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_crypto_intents_tenant_status ON crypto_payment_intents(tenant_id, status);
    CREATE INDEX IF NOT EXISTS idx_crypto_intents_expiry ON crypto_payment_intents(payment_expires_at);
    """)
