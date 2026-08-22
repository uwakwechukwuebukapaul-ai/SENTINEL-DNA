"""Tenant-scoped append-only operational alert ownership history."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


class OperationalAlertAssignmentRepository:
    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operational_alert_assignment_events (
                event_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
                actor_id TEXT NOT NULL, assignee_id TEXT, state TEXT NOT NULL,
                event_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_assignment_alert ON operational_alert_assignment_events(tenant_id, alert_id, created_at)")

    def append(self, *, alert_id: str, tenant_id: str, actor_id: str, assignee_id: str | None, state: str, reason: str = ""):
        tenant_id, actor_id, alert_id = str(tenant_id or "").strip(), str(actor_id or "").strip(), str(alert_id or "").strip()
        if not tenant_id or not actor_id or not alert_id:
            raise PermissionError("alert_assignment_context_required")
        if state not in {"unassigned", "assigned", "acknowledged", "in_progress", "resolved"}:
            raise ValueError("invalid_operational_alert_assignment_state")
        event = {"event_id": f"OAA-{uuid4().hex}", "alert_id": alert_id, "tenant_id": tenant_id,
                 "actor_id": actor_id, "assignee_id": str(assignee_id) if assignee_id else None,
                 "state": state, "reason": str(reason or "").strip()[:2000],
                 "created_at": datetime.now(timezone.utc).isoformat()}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operational_alert_assignment_events(event_id, alert_id, tenant_id, actor_id, assignee_id, state, event_json, created_at) VALUES(?,?,?,?,?,?,?,?)",
                               (event["event_id"], alert_id, tenant_id, actor_id, event["assignee_id"], state, json.dumps(event, sort_keys=True), event["created_at"]))
        return event

    def history(self, alert_id: str, *, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute("SELECT event_json FROM operational_alert_assignment_events WHERE alert_id=? AND tenant_id=? ORDER BY created_at, rowid", (str(alert_id), str(tenant_id))).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def page_history(self, alert_id: str, *, tenant_id: str, page=1, page_size=25):
        page, page_size = int(page), int(page_size)
        if page < 1 or page_size < 1 or page_size > 100: raise ValueError("invalid_pagination")
        offset = (page - 1) * page_size
        with self.db.session() as connection:
            rows = connection.execute("SELECT event_json FROM operational_alert_assignment_events WHERE alert_id=? AND tenant_id=? ORDER BY created_at, rowid LIMIT ? OFFSET ?", (str(alert_id), str(tenant_id), page_size, offset)).fetchall()
            total = connection.execute("SELECT COUNT(*) AS total FROM operational_alert_assignment_events WHERE alert_id=? AND tenant_id=?", (str(alert_id), str(tenant_id))).fetchone()["total"]
        return {"items": [json.loads(row["event_json"]) for row in rows], "page": page, "page_size": page_size, "total": int(total), "has_next": offset + page_size < int(total)}

    def current(self, alert_id: str, *, tenant_id: str):
        items = self.history(alert_id, tenant_id=tenant_id)
        return items[-1] if items else {"state": "unassigned", "assignee_id": None}

    def list_for_tenant(self, *, tenant_id: str):
        latest = {}
        with self.db.session() as connection:
            rows = connection.execute("SELECT alert_id, event_json FROM operational_alert_assignment_events WHERE tenant_id=? ORDER BY created_at, rowid", (str(tenant_id),)).fetchall()
        for row in rows:
            latest[str(row["alert_id"])] = json.loads(row["event_json"])
        return list(latest.values())
