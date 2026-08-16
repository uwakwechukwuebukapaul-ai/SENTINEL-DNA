"""Provider-neutral durable billing repository."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from database.connection import DatabaseConnection, database
from .exceptions import BillingError

def ensure_billing_schema(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS billing_customers (tenant_id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_customer_id TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS billing_transactions (transaction_reference TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, provider TEXT NOT NULL, provider_transaction_id TEXT UNIQUE, plan_id TEXT NOT NULL, status TEXT NOT NULL, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, verified_at TEXT);
    CREATE TABLE IF NOT EXISTS billing_subscriptions (tenant_id TEXT PRIMARY KEY, provider TEXT NOT NULL, plan_id TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS billing_events (event_id TEXT PRIMARY KEY, provider TEXT NOT NULL, event_type TEXT NOT NULL, transaction_reference TEXT, received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS billing_checkout_requests (tenant_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, transaction_reference TEXT NOT NULL UNIQUE, plan_id TEXT NOT NULL, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, authorization_url TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(tenant_id,idempotency_key));
    CREATE INDEX IF NOT EXISTS idx_billing_transactions_tenant ON billing_transactions(tenant_id);
    """)

class BillingRepository:
    def __init__(self, db: DatabaseConnection = database): self.db=db
    @contextmanager
    def transaction(self):
        with self.db.session() as connection:
            ensure_billing_schema(connection)
            yield connection
    def tenant_active(self, connection, tenant_id):
        row=connection.execute("SELECT status FROM canonical_tenants WHERE tenant_id=?",(tenant_id,)).fetchone()
        if not row or row["status"] != "active": raise BillingError("canonical_tenant_inactive_or_missing")
    def create_transaction(self, connection, tenant_id, reference, provider, plan_id, amount_minor, currency):
        self.tenant_active(connection,tenant_id); connection.execute("INSERT INTO billing_transactions(transaction_reference,tenant_id,provider,plan_id,status,amount_minor,currency) VALUES(?,?,?,?,?,?,?)",(reference,tenant_id,provider,plan_id,"PENDING",int(amount_minor),currency))
    def get_transaction(self, connection, reference): return connection.execute("SELECT * FROM billing_transactions WHERE transaction_reference=?",(reference,)).fetchone()
    def get_transaction_by_provider(self, connection, provider_reference): return connection.execute("SELECT * FROM billing_transactions WHERE provider_transaction_id=?",(provider_reference,)).fetchone()
    def latest_transaction(self, connection, tenant_id): return connection.execute("SELECT * FROM billing_transactions WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1",(tenant_id,)).fetchone()
    def update_transaction(self, connection, reference, status, provider_reference=None): connection.execute("UPDATE billing_transactions SET status=?,provider_transaction_id=COALESCE(?,provider_transaction_id),verified_at=CURRENT_TIMESTAMP WHERE transaction_reference=?",(status,provider_reference,reference))
    def get_subscription(self, connection, tenant_id): return connection.execute("SELECT * FROM billing_subscriptions WHERE tenant_id=?",(tenant_id,)).fetchone()
    def save_subscription(self, connection, tenant_id, provider, plan_id, status): self.tenant_active(connection,tenant_id); connection.execute("INSERT INTO billing_subscriptions(tenant_id,provider,plan_id,status) VALUES(?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET provider=excluded.provider,plan_id=excluded.plan_id,status=excluded.status,updated_at=CURRENT_TIMESTAMP",(tenant_id,provider,plan_id,status))
    def event_exists(self, connection, event_id): return connection.execute("SELECT 1 FROM billing_events WHERE event_id=?",(event_id,)).fetchone() is not None
    def record_event(self, connection, event_id, provider, event_type, transaction_reference=None):
        try: connection.execute("INSERT INTO billing_events(event_id,provider,event_type,transaction_reference) VALUES(?,?,?,?)",(event_id,provider,event_type,transaction_reference)); return True
        except sqlite3.IntegrityError: return False
    def get_checkout(self, connection, tenant_id, idempotency_key): return connection.execute("SELECT * FROM billing_checkout_requests WHERE tenant_id=? AND idempotency_key=?",(tenant_id,idempotency_key)).fetchone()
    def save_checkout(self, connection, tenant_id, key, result): connection.execute("INSERT INTO billing_checkout_requests(tenant_id,idempotency_key,transaction_reference,plan_id,amount_minor,currency,authorization_url) VALUES(?,?,?,?,?,?,?)",(tenant_id,key,result.transaction_reference,result.plan_id,result.amount_minor,result.currency,result.authorization_url))
