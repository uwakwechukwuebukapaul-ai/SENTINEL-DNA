"""Tenant-scoped, append-only operational alert policy history."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


class OperationalAlertPolicyRepository:
    """Persist policy configuration only; metrics remain derived from canonical stores."""

    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operational_alert_policy_events (
                event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, rule TEXT NOT NULL,
                actor_id TEXT NOT NULL, event_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_policy_tenant ON operational_alert_policy_events(tenant_id, rule, created_at)")

    def append(self, *, tenant_id: str, rule: str, threshold: float, enabled: bool = True,
               severity: str = "medium", actor_id: str, reason: str = "", previous_value=None):
        tenant_id, rule, actor_id = str(tenant_id or "").strip(), str(rule or "").strip(), str(actor_id or "").strip()
        if not tenant_id or not actor_id:
            raise PermissionError("policy_tenant_and_actor_required")
        history = self._events(tenant_id, rule)
        event = {"event_id": f"OPE-{uuid4().hex}", "tenant_id": tenant_id, "rule": rule,
                 "version": len(history) + 1, "threshold": threshold, "enabled": bool(enabled), "severity": severity,
                 "previous_value": previous_value, "new_value": {"threshold": threshold, "enabled": bool(enabled), "severity": severity},
                 "changed_by": actor_id, "actor_id": actor_id, "reason": str(reason or "").strip()[:2000], "created_at": datetime.now(timezone.utc).isoformat()}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operational_alert_policy_events(event_id, tenant_id, rule, actor_id, event_json, created_at) VALUES(?,?,?,?,?,?)",
                               (event["event_id"], tenant_id, rule, actor_id, json.dumps(event, sort_keys=True), event["created_at"]))
        return event

    def _events(self, tenant_id: str, rule: str | None = None):
        query = "SELECT event_json FROM operational_alert_policy_events WHERE tenant_id=?"
        params = [str(tenant_id)]
        if rule is not None:
            query += " AND rule=?"; params.append(str(rule))
        query += " ORDER BY created_at, rowid"
        with self.db.session() as connection:
            rows = connection.execute(query, params).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def list_for_tenant(self, *, tenant_id: str):
        latest = {}
        for event in self._events(tenant_id):
            latest[event["rule"]] = event
        return list(latest.values())

    def get(self, rule: str, *, tenant_id: str):
        items = self._events(tenant_id, rule)
        return items[-1] if items else None

    def history(self, *, tenant_id: str, rule: str | None = None):
        return self._events(tenant_id, rule)

    def page_history(self, *, tenant_id: str, rule: str | None = None, page=1, page_size=25):
        page, page_size = int(page), int(page_size)
        if page < 1 or page_size < 1 or page_size > 100: raise ValueError("invalid_pagination")
        offset = (page - 1) * page_size
        query = "SELECT event_json FROM operational_alert_policy_events WHERE tenant_id=?"; params = [str(tenant_id)]
        count_query = "SELECT COUNT(*) AS total FROM operational_alert_policy_events WHERE tenant_id=?"
        if rule is not None: query += " AND rule=?"; count_query += " AND rule=?"; params.append(str(rule))
        query += " ORDER BY created_at, rowid LIMIT ? OFFSET ?"
        with self.db.session() as connection:
            rows = connection.execute(query, (*params, page_size, offset)).fetchall()
            total = connection.execute(count_query, params).fetchone()["total"]
        return {"items": [json.loads(row["event_json"]) for row in rows], "page": page, "page_size": page_size, "total": int(total), "has_next": offset + page_size < int(total)}
