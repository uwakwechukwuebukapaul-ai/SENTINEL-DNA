"""Durable canonical tenant, identity, and membership authority."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

from .connection import DatabaseConnection, database
from .portability import execute_script, identity_primary_key


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_canonical_schema(connection: Any, *, commit: bool = True) -> None:
    """Create only the additive canonical foundation tables."""
    identity = identity_primary_key(getattr(connection, "backend_name", "sqlite"))
    execute_script(
        connection,
        f"""
        CREATE TABLE IF NOT EXISTS audit_events (
            id {identity},
            event_type TEXT NOT NULL,
            case_id TEXT,
            user_id INTEGER,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS canonical_tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'deleted')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_canonical_tenants_status
            ON canonical_tenants(status);

        CREATE TABLE IF NOT EXISTS canonical_identities (
            actor_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'deleted')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_canonical_identities_email
            ON canonical_identities(email);

        CREATE TABLE IF NOT EXISTS canonical_memberships (
            tenant_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, actor_id),
            FOREIGN KEY (tenant_id) REFERENCES canonical_tenants(tenant_id),
            FOREIGN KEY (actor_id) REFERENCES canonical_identities(actor_id)
        );
        CREATE INDEX IF NOT EXISTS idx_canonical_memberships_actor
            ON canonical_memberships(actor_id);

        CREATE TABLE IF NOT EXISTS canonical_identity_bindings (
            binding_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            external_subject TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'disabled', 'revoked')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            revoked_at TEXT,
            UNIQUE (provider, external_subject),
            FOREIGN KEY (actor_id) REFERENCES canonical_identities(actor_id)
        );
        CREATE INDEX IF NOT EXISTS idx_canonical_identity_bindings_actor
            ON canonical_identity_bindings(actor_id);

        CREATE TABLE IF NOT EXISTS canonical_provider_tenant_trusts (
            trust_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            issuer TEXT NOT NULL,
            external_tenant_id TEXT NOT NULL,
            canonical_tenant_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'disabled', 'revoked')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            revoked_at TEXT,
            UNIQUE (provider, issuer, external_tenant_id),
            FOREIGN KEY (canonical_tenant_id) REFERENCES canonical_tenants(tenant_id)
        );
        CREATE INDEX IF NOT EXISTS idx_provider_tenant_trust_canonical
            ON canonical_provider_tenant_trusts(canonical_tenant_id);

        CREATE TABLE IF NOT EXISTS canonical_schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT INTO canonical_schema_metadata(key, value)
            VALUES ('authority_version', '1')
            ON CONFLICT (key) DO NOTHING;
        """
    )
    # The legacy SQLite schema API committed setup here. Preserve that
    # boundary because legacy authorization flows may open a nested,
    # read-only unit of work on the same SQLite database.
    if commit:
        connection.commit()


class CanonicalUnitOfWork:
    """One SQLite connection shared by canonical repositories and audit."""

    def __init__(self, db: DatabaseConnection = database) -> None:
        self.db = db
        self.connection: Any | None = None

    def __enter__(self) -> "CanonicalUnitOfWork":
        self.connection = self.db.connect()
        try:
            ensure_canonical_schema(self.connection)
            return self
        except Exception:
            self.connection.rollback()
            self.connection.close()
            self.connection = None
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        assert self.connection is not None
        try:
            if exc_type:
                self.connection.rollback()
            else:
                self.connection.commit()
        finally:
            self.connection.close()
            self.connection = None

    @property
    def conn(self) -> Any:
        if self.connection is None:
            raise RuntimeError("canonical_unit_of_work_not_active")
        return self.connection


class CanonicalTenantRepository:
    def __init__(self, connection: Any): self.connection = connection

    def create(self, name: str, tenant_id: str | None = None):
        tenant_id = tenant_id or str(uuid4()); now = _now()
        self.connection.execute(
            "INSERT INTO canonical_tenants VALUES (?, ?, 'active', ?, ?)",
            (tenant_id, str(name).strip(), now, now),
        )
        return self.get(tenant_id)

    def get(self, tenant_id: str):
        return self.connection.execute("SELECT * FROM canonical_tenants WHERE tenant_id=?", (tenant_id,)).fetchone()

    def set_status(self, tenant_id: str, status: str):
        self.connection.execute("UPDATE canonical_tenants SET status=?, updated_at=? WHERE tenant_id=?", (status, _now(), tenant_id))
        return self.get(tenant_id)


class CanonicalIdentityRepository:
    def __init__(self, connection: Any): self.connection = connection

    def create(self, email: str, display_name: str = "", actor_id: str | None = None):
        actor_id = actor_id or str(uuid4()); now = _now()
        self.connection.execute(
            "INSERT INTO canonical_identities VALUES (?, ?, ?, 'active', ?, ?)",
            (actor_id, str(email).strip().lower(), display_name, now, now),
        )
        return self.get(actor_id)

    def get(self, actor_id: str):
        return self.connection.execute("SELECT * FROM canonical_identities WHERE actor_id=?", (actor_id,)).fetchone()


class CanonicalMembershipRepository:
    def __init__(self, connection: Any): self.connection = connection

    def add(self, tenant_id: str, actor_id: str, role: str = "viewer"):
        now = _now()
        self.connection.execute(
            "INSERT INTO canonical_memberships VALUES (?, ?, ?, 'active', ?, ?)",
            (tenant_id, actor_id, role, now, now),
        )
        return self.get(tenant_id, actor_id)

    def get(self, tenant_id: str, actor_id: str):
        return self.connection.execute(
            "SELECT * FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (tenant_id, actor_id)
        ).fetchone()

    def list_for_actor(self, actor_id: str):
        return self.connection.execute("SELECT * FROM canonical_memberships WHERE actor_id=?", (actor_id,)).fetchall()

    def list_for_tenant(self, tenant_id: str):
        return self.connection.execute("SELECT * FROM canonical_memberships WHERE tenant_id=?", (tenant_id,)).fetchall()


class CanonicalIdentityBindingRepository:
    def __init__(self, connection: Any): self.connection = connection

    def create(self, provider: str, external_subject: str, actor_id: str, created_by: str, binding_id: str | None = None):
        binding_id = binding_id or str(uuid4()); now = _now()
        self.connection.execute(
            "INSERT INTO canonical_identity_bindings VALUES (?, ?, ?, ?, 'active', ?, ?, ?, NULL)",
            (binding_id, provider, external_subject, actor_id, now, now, created_by),
        )
        return self.get(provider, external_subject)

    def get(self, provider: str, external_subject: str):
        return self.connection.execute(
            "SELECT * FROM canonical_identity_bindings WHERE provider=? AND external_subject=?",
            (provider, external_subject),
        ).fetchone()

    def get_by_id(self, binding_id: str):
        return self.connection.execute("SELECT * FROM canonical_identity_bindings WHERE binding_id=?", (binding_id,)).fetchone()

    def set_status(self, binding_id: str, status: str):
        revoked_at = _now() if status == "revoked" else None
        self.connection.execute(
            "UPDATE canonical_identity_bindings SET status=?, updated_at=?, revoked_at=? WHERE binding_id=?",
            (status, _now(), revoked_at, binding_id),
        )
        return self.connection.execute("SELECT * FROM canonical_identity_bindings WHERE binding_id=?", (binding_id,)).fetchone()


class ProviderTenantTrustRepository:
    def __init__(self, connection: Any): self.connection = connection
    def create(self, provider, issuer, external_tenant_id, canonical_tenant_id, created_by, trust_id=None):
        trust_id = trust_id or str(uuid4()); now = _now()
        self.connection.execute("INSERT INTO canonical_provider_tenant_trusts VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL)", (trust_id, provider, issuer, external_tenant_id, canonical_tenant_id, now, now, created_by))
        return self.get(provider, issuer, external_tenant_id)
    def get(self, provider, issuer, external_tenant_id):
        return self.connection.execute("SELECT * FROM canonical_provider_tenant_trusts WHERE provider=? AND issuer=? AND external_tenant_id=?", (provider, issuer, external_tenant_id)).fetchone()
    def get_by_id(self, trust_id): return self.connection.execute("SELECT * FROM canonical_provider_tenant_trusts WHERE trust_id=?", (trust_id,)).fetchone()
    def set_status(self, trust_id, status):
        revoked_at = _now() if status == 'revoked' else None
        self.connection.execute("UPDATE canonical_provider_tenant_trusts SET status=?, updated_at=?, revoked_at=? WHERE trust_id=?", (status, _now(), revoked_at, trust_id))
        return self.get_by_id(trust_id)
