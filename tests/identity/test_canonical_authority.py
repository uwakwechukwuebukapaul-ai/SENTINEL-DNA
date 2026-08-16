import sqlite3

import pytest

from database.canonical_authority import CanonicalUnitOfWork, CanonicalTenantRepository, CanonicalIdentityRepository, CanonicalMembershipRepository
from database.connection import DatabaseConnection
from services.audit.service import AuditService


def db(tmp_path):
    return DatabaseConnection(tmp_path / "canonical.db")


def test_canonical_authorities_and_audit_commit_together(tmp_path):
    database = db(tmp_path)
    audit = AuditService(database)
    with CanonicalUnitOfWork(database) as unit:
        tenant = CanonicalTenantRepository(unit.conn).create("Acme", "tenant-1")
        actor = CanonicalIdentityRepository(unit.conn).create("a@example.com", actor_id="actor-1")
        membership = CanonicalMembershipRepository(unit.conn).add(tenant["tenant_id"], actor["actor_id"], "admin")
        audit.record("CANONICAL_MEMBERSHIP_CREATED", details={"tenant_id": tenant["tenant_id"]}, connection=unit.conn)
        assert membership["role"] == "admin"
    with database.session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM canonical_memberships").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='CANONICAL_MEMBERSHIP_CREATED'").fetchone()[0] == 1


def test_canonical_unit_of_work_rolls_back_authority_and_audit(tmp_path):
    database = db(tmp_path)
    audit = AuditService(database)
    with pytest.raises(RuntimeError):
        with CanonicalUnitOfWork(database) as unit:
            tenant = CanonicalTenantRepository(unit.conn).create("Acme", "tenant-1")
            audit.record("SHOULD_ROLLBACK", connection=unit.conn)
            raise RuntimeError("abort")
    with database.session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM canonical_tenants").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='SHOULD_ROLLBACK'").fetchone()[0] == 0


def test_membership_requires_existing_canonical_records(tmp_path):
    database = db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        with CanonicalUnitOfWork(database) as unit:
            CanonicalMembershipRepository(unit.conn).add("missing-tenant", "missing-actor")
