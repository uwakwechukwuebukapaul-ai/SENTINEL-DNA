"""SaaS database boundary supporting SQLite development and PostgreSQL production."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
import os
from pathlib import Path


SAAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    membership_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, organization_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS usage_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    event_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
);

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
    plan_id TEXT NOT NULL,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_subscription_id TEXT,
    current_period_start TEXT NOT NULL,
    current_period_end TEXT NOT NULL,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(plan_id) REFERENCES billing_plans(plan_id)
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

CREATE TABLE IF NOT EXISTS billing_provider_events (
    provider_event_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tenant_id TEXT,
    processed_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_type_time ON usage_events(tenant_id, event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tenant ON billing_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscription_events_tenant_time ON subscription_events(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_time ON invoices(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_billing_provider_events_tenant ON billing_provider_events(tenant_id, processed_at);
"""


def _postgres_migrations() -> list[str]:
    """Load versioned PostgreSQL migrations without duplicating application models."""
    migrations_dir = Path(__file__).with_name("migrations")
    return [
        migration.read_text(encoding="utf-8")
        for migration in sorted(migrations_dir.glob("*.postgresql.sql"))
    ]


class SaaSDatabase:
    def __init__(self, data_dir: str | Path = "data", database_url: str | None = None) -> None:
        self.database_url = database_url if database_url is not None else os.getenv("SENTINEL_DNA_SAAS_DATABASE_URL")
        self.backend = "postgresql" if self.database_url else "sqlite"
        self.data_dir = Path(data_dir)
        self.database = self.data_dir / "sentinel_dna_saas.db"
        if self.backend == "sqlite":
            self.data_dir.mkdir(parents=True, exist_ok=True)
        elif not self.database_url or not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("PostgreSQL database URL is required")
        self.initialize()

    @contextmanager
    def connect(self):
        if self.backend == "sqlite":
            connection = sqlite3.connect(self.database)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
        else:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("PostgreSQL support requires psycopg; install sentinel-dna[postgres]") from exc
            connection = psycopg.connect(self.database_url, row_factory=dict_row)
        try:
            yield _PostgresCompatibleConnection(connection) if self.backend == "postgresql" else connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            if self.backend == "sqlite":
                connection.executescript(SAAS_SCHEMA)
            else:
                for migration in _postgres_migrations():
                    for statement in migration.split(";"):
                        if statement.strip():
                            connection.execute(statement)

    def is_ready(self) -> bool:
        with self.connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return True


class _PostgresCompatibleConnection:
    """Adapts existing SQLite qmark queries to psycopg's parameter style."""

    def __init__(self, connection) -> None:
        self._connection = connection

    def execute(self, query: str, parameters=()):
        return self._connection.execute(query.replace("?", "%s"), parameters)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()
