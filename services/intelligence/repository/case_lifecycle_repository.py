"""Append-only case closure and report approval lifecycle events."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4


class CaseLifecycleRepository:
    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS investigation_lifecycle_events (
                event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, event_kind TEXT NOT NULL,
                state TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}')""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_case ON investigation_lifecycle_events(tenant_id, case_id, created_at)")

    def append(self, *, case_id, investigation_id, tenant_id, actor_id, event_kind, state, reason="", details=None):
        event = {"event_id": f"LCE-{uuid4().hex}", "case_id": str(case_id), "investigation_id": str(investigation_id), "tenant_id": str(tenant_id), "actor_id": str(actor_id), "event_kind": str(event_kind), "state": str(state), "reason": str(reason or "").strip()[:2000], "created_at": datetime.now(timezone.utc).isoformat(), "details": dict(details or {})}
        with self.db.session() as connection:
            connection.execute("INSERT INTO investigation_lifecycle_events (event_id, case_id, investigation_id, tenant_id, actor_id, event_kind, state, reason, created_at, details_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event["event_id"], event["case_id"], event["investigation_id"], event["tenant_id"], event["actor_id"], event["event_kind"], event["state"], event["reason"], event["created_at"], json.dumps(event["details"])))
        return event

    def list_for_case(self, case_id, *, tenant_id):
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM investigation_lifecycle_events WHERE case_id=? AND tenant_id=? ORDER BY rowid", (str(case_id), str(tenant_id))).fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"] or "{}")} for row in rows]

    def list_for_tenant(self, *, tenant_id):
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM investigation_lifecycle_events WHERE tenant_id=? ORDER BY created_at, rowid",
                (str(tenant_id),),
            ).fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"] or "{}")} for row in rows]

    def latest(self, case_id, *, tenant_id, event_kind=None):
        items = self.list_for_case(case_id, tenant_id=tenant_id)
        if event_kind:
            items = [item for item in items if item["event_kind"] == event_kind]
        return items[-1] if items else None

    def assignments(self, case_id, *, tenant_id):
        return [item for item in self.list_for_case(case_id, tenant_id=tenant_id) if item["event_kind"] == "assignment"]

    def latest_assignment(self, case_id, *, tenant_id):
        items = self.assignments(case_id, tenant_id=tenant_id)
        return items[-1] if items else None

    def latest_sla(self, case_id, *, tenant_id):
        return self.latest(case_id, tenant_id=tenant_id, event_kind="sla")

    def latest_escalation(self, case_id, *, tenant_id):
        return self.latest(case_id, tenant_id=tenant_id, event_kind="escalation")
