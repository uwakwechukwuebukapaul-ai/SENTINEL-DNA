import json

import pytest

from database.connection import DatabaseConnection
from database.errors import DatabaseError
from services.audit.service import AuditService


def test_audit_events_are_tenant_aware_redacted_and_append_only(tmp_path):
    service = AuditService(DatabaseConnection(tmp_path / "audit.db"))
    event_id = service.record(
        "INVESTIGATION_COMPLETED",
        tenant_id="tenant-a",
        actor_id="actor-a",
        correlation_id="corr-1",
        request_id="req-1",
        resource_type="execution",
        resource_id="EXE-1",
        operation="complete",
        outcome="success",
        latency_ms=12.5,
        details={"safe": "value", "api_token": "must-not-persist", "nested": {"password": "hidden"}},
    )

    row = service.get_for_tenant(event_id, "tenant-a")
    assert row is not None
    assert row["event_id"] == event_id
    assert row["tenant_id"] == "tenant-a"
    assert row["correlation_id"] == "corr-1"
    assert row["schema_version"] == "audit-event-v1"
    assert row["details"]["safe"] == "value"
    assert row["details"]["api_token"] == "[REDACTED]"
    assert row["details"]["nested"]["password"] == "[REDACTED]"
    assert service.get_for_tenant(event_id, "tenant-b") is None

    with pytest.raises(DatabaseError):
        with service.db.session() as connection:
            connection.execute("UPDATE audit_events SET outcome='tampered' WHERE event_id=?", (event_id,))

    with pytest.raises(DatabaseError):
        with service.db.session() as connection:
            connection.execute("DELETE FROM audit_events WHERE event_id=?", (event_id,))


def test_audit_list_is_scoped_and_legacy_callers_remain_compatible(tmp_path):
    service = AuditService(DatabaseConnection(tmp_path / "audit.db"))
    service.record("A", details={"tenant_id": "tenant-a"}, tenant_id="tenant-a")
    service.record("B", tenant_id="tenant-b")
    service.record("LEGACY", details={"case": "CASE-1"})

    assert [item["event_type"] for item in service.list_for_tenant("tenant-a")] == ["A"]
    with service.db.session() as connection:
        raw = connection.execute("SELECT details_json FROM audit_events WHERE event_type='LEGACY'").fetchone()[0]
    assert json.loads(raw) == {"case": "CASE-1"}
