"""Append-only persistence for operational alert detections and lifecycle actions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


class OperationalAlertRepository:
    """Store alert metadata only; investigation and provider records remain canonical."""

    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operational_alert_events (
                event_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
                event_kind TEXT NOT NULL, state TEXT NOT NULL, actor_id TEXT,
                event_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_alert_tenant ON operational_alert_events(tenant_id, alert_id, created_at)")

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def append(self, alert: dict, *, tenant_id: str, event_kind: str, state: str, actor_id: str | None = None):
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise PermissionError("alert_tenant_required")
        event = {"event_id": f"OAE-{uuid4().hex}", "alert_id": str(alert["alert_id"]), "tenant_id": tenant_id,
                 "event_kind": str(event_kind), "state": str(state), "actor_id": actor_id,
                 "created_at": self._now(), "alert": {key: alert.get(key) for key in (
                     "alert_id", "rule", "severity", "reason", "metric_source", "observed_value",
                     "operator", "threshold", "provider", "detected_at")}}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operational_alert_events(event_id, alert_id, tenant_id, event_kind, state, actor_id, event_json, created_at) VALUES(?,?,?,?,?,?,?,?)",
                               (event["event_id"], event["alert_id"], tenant_id, event["event_kind"], state, actor_id, json.dumps(event, sort_keys=True, default=str), event["created_at"]))
        return event

    def _events(self, tenant_id: str, alert_id: str | None = None):
        query = "SELECT event_json FROM operational_alert_events WHERE tenant_id=?"
        params = [str(tenant_id)]
        if alert_id is not None:
            query += " AND alert_id=?"; params.append(str(alert_id))
        query += " ORDER BY created_at, rowid"
        with self.db.session() as connection:
            rows = connection.execute(query, params).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def latest(self, alert_id: str, *, tenant_id: str):
        events = self._events(tenant_id, alert_id)
        return events[-1] if events else None

    def list_for_tenant(self, *, tenant_id: str):
        latest = {}
        for event in self._events(tenant_id):
            latest[event["alert_id"]] = event
        return list(latest.values())

    def has_detection(self, alert_id: str, *, tenant_id: str):
        return any(event["event_kind"] == "detected" for event in self._events(tenant_id, alert_id))
