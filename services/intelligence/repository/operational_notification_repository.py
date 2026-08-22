"""Durable tenant-scoped notification delivery attempts and leases."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class OperationalNotificationRepository:
    STATUSES = {"pending", "leased", "sending", "sent", "delivered", "retry_scheduled", "failed", "suppressed", "dead_lettered"}

    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operational_notification_attempts (
                delivery_id TEXT PRIMARY KEY, notification_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
                alert_id TEXT NOT NULL, policy_id TEXT NOT NULL, idempotency_key TEXT,
                adapter TEXT NOT NULL, status TEXT NOT NULL, actor_source TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0, suppression_reason TEXT,
                attempted_at TEXT NOT NULL, lease_id TEXT, worker_id TEXT,
                acquired_at TEXT, expires_at TEXT, released_at TEXT,
                attempt_json TEXT NOT NULL)""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(operational_notification_attempts)").fetchall()}
            for name, definition in (("notification_id", "TEXT"), ("policy_id", "TEXT NOT NULL DEFAULT ''"), ("idempotency_key", "TEXT"), ("actor_source", "TEXT NOT NULL DEFAULT 'system'"), ("retry_count", "INTEGER NOT NULL DEFAULT 0"), ("suppression_reason", "TEXT"), ("destination", "TEXT"), ("lease_id", "TEXT"), ("worker_id", "TEXT"), ("acquired_at", "TEXT"), ("expires_at", "TEXT"), ("released_at", "TEXT"), ("next_attempt_at", "TEXT"), ("attempt_history_json", "TEXT NOT NULL DEFAULT '[]'")):
                if name not in columns:
                    connection.execute(f"ALTER TABLE operational_notification_attempts ADD COLUMN {name} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_notification_tenant ON operational_notification_attempts(tenant_id, attempted_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_notification_idempotency ON operational_notification_attempts(tenant_id, idempotency_key)")

    def append(self, *, tenant_id: str, alert_id: str, adapter: str, status: str, detail: str = "", policy_id: str = "", actor_source: str = "system", retry_count: int = 0, suppression_reason: str | None = None, idempotency_key: str | None = None, notification_id: str | None = None, destination: str | None = None, next_attempt_at: str | None = None, attempt_history=None):
        if status not in self.STATUSES and status != "simulated": raise ValueError("invalid_notification_attempt_status")
        if idempotency_key:
            existing = self.get_by_idempotency(idempotency_key, tenant_id=tenant_id)
            if existing: return existing
        now = datetime.now(timezone.utc).isoformat()
        event = {"delivery_id": f"OND-{uuid4().hex}", "notification_id": notification_id or f"NTF-{uuid4().hex}", "tenant_id": str(tenant_id), "alert_id": str(alert_id), "policy_id": str(policy_id), "idempotency_key": idempotency_key, "adapter": str(adapter), "destination": destination, "status": str(status), "actor_source": str(actor_source), "retry_count": int(retry_count), "suppression_reason": suppression_reason, "next_attempt_at": next_attempt_at, "attempt_history": list(attempt_history or []), "detail": str(detail or "")[:1000], "attempted_at": now, "lease_id": None, "worker_id": None, "acquired_at": None, "expires_at": None, "released_at": None}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operational_notification_attempts(delivery_id, notification_id, tenant_id, alert_id, policy_id, idempotency_key, adapter, destination, status, actor_source, retry_count, suppression_reason, attempted_at, attempt_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event["delivery_id"], event["notification_id"], event["tenant_id"], event["alert_id"], event["policy_id"], event["idempotency_key"], event["adapter"], event["destination"], event["status"], event["actor_source"], event["retry_count"], event["suppression_reason"], now, json.dumps(event, sort_keys=True)))
        return event

    def _decode(self, row):
        value = json.loads(row["attempt_json"])
        value.setdefault("next_attempt_at", row["next_attempt_at"]); value.setdefault("attempt_history", json.loads(row["attempt_history_json"] or "[]"))
        for key in ("notification_id", "policy_id", "idempotency_key", "actor_source", "retry_count", "suppression_reason", "destination", "lease_id", "worker_id", "acquired_at", "expires_at", "released_at"):
            if key in {"lease_id", "worker_id", "acquired_at", "expires_at", "released_at"} or key not in value: value[key] = row[key]
        return value

    def get_by_idempotency(self, idempotency_key: str, *, tenant_id: str):
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM operational_notification_attempts WHERE tenant_id=? AND idempotency_key=? ORDER BY rowid LIMIT 1", (str(tenant_id), str(idempotency_key))).fetchone()
        return self._decode(row) if row else None

    def get(self, delivery_id: str, *, tenant_id: str):
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM operational_notification_attempts WHERE delivery_id=? AND tenant_id=?", (str(delivery_id), str(tenant_id))).fetchone()
        return self._decode(row) if row else None

    def list_for_tenant(self, *, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operational_notification_attempts WHERE tenant_id=? ORDER BY attempted_at, rowid", (str(tenant_id),)).fetchall()
        return [self._decode(row) for row in rows]

    def page_for_tenant(self, *, tenant_id: str, page=1, page_size=25):
        page, page_size = int(page), int(page_size)
        if page < 1 or page_size < 1 or page_size > 100: raise ValueError("invalid_pagination")
        offset = (page - 1) * page_size
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operational_notification_attempts WHERE tenant_id=? ORDER BY attempted_at, rowid LIMIT ? OFFSET ?", (str(tenant_id), page_size, offset)).fetchall()
            total = connection.execute("SELECT COUNT(*) AS total FROM operational_notification_attempts WHERE tenant_id=?", (str(tenant_id),)).fetchone()["total"]
        return {"items": [self._decode(row) for row in rows], "page": page, "page_size": page_size, "total": int(total), "has_next": offset + page_size < int(total)}

    def acquire_lease(self, delivery_id: str, *, tenant_id: str, worker_id: str, lease_seconds: int = 300, now=None):
        now = now or datetime.now(timezone.utc); expires = (now + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operational_notification_attempts SET lease_id=?, worker_id=?, acquired_at=?, expires_at=?, status='leased' WHERE delivery_id=? AND tenant_id=? AND status IN ('pending','retry_scheduled') AND (expires_at IS NULL OR expires_at<=?)", (f"NLE-{uuid4().hex}", str(worker_id), now.isoformat(), expires, str(delivery_id), str(tenant_id), now.isoformat()))
            if cursor.rowcount != 1: return None
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM operational_notification_attempts WHERE delivery_id=? AND tenant_id=?", (str(delivery_id), str(tenant_id))).fetchone()
        return self._decode(row) if row else None

    def renew_lease(self, delivery_id: str, *, tenant_id: str, worker_id: str, lease_id: str, lease_seconds: int = 300, now=None):
        now = now or datetime.now(timezone.utc); expires = (now + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operational_notification_attempts SET expires_at=? WHERE delivery_id=? AND tenant_id=? AND worker_id=? AND lease_id=? AND expires_at>?", (expires, str(delivery_id), str(tenant_id), str(worker_id), str(lease_id), now.isoformat()))
        return cursor.rowcount == 1

    def update(self, delivery_id: str, *, tenant_id: str, status: str, detail: str = "", retry_count: int | None = None, next_attempt_at: str | None = None, attempt_history=None, lease_id: str | None = None, worker_id: str | None = None):
        current = self.get(delivery_id, tenant_id=tenant_id)
        if not current: return None
        current.update({"status": status, "detail": str(detail or "")[:1000], "retry_count": int(retry_count if retry_count is not None else current.get("retry_count", 0)), "next_attempt_at": next_attempt_at if next_attempt_at is not None else current.get("next_attempt_at"), "attempt_history": list(attempt_history if attempt_history is not None else current.get("attempt_history", []))})
        query = "UPDATE operational_notification_attempts SET status=?, attempt_json=?, retry_count=?, next_attempt_at=?, attempt_history_json=? WHERE delivery_id=? AND tenant_id=?"; params = [status, json.dumps(current, sort_keys=True), current["retry_count"], current["next_attempt_at"], json.dumps(current["attempt_history"]), str(delivery_id), str(tenant_id)]
        if lease_id is not None: query += " AND lease_id=? AND worker_id=?"; params.extend([str(lease_id), str(worker_id)])
        with self.db.session() as connection:
            cursor = connection.execute(query, params)
        return current if lease_id is None or cursor.rowcount == 1 else None

    def release_lease(self, delivery_id: str, *, tenant_id: str, worker_id: str, lease_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operational_notification_attempts SET released_at=?, lease_id=NULL, worker_id=NULL, acquired_at=NULL, expires_at=NULL WHERE delivery_id=? AND tenant_id=? AND worker_id=? AND lease_id=?", (now.isoformat(), str(delivery_id), str(tenant_id), str(worker_id), str(lease_id)))
        return cursor.rowcount == 1

    def list_expired_leases(self, *, tenant_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operational_notification_attempts WHERE tenant_id=? AND lease_id IS NOT NULL AND expires_at IS NOT NULL AND expires_at<=? ORDER BY expires_at, rowid LIMIT 100", (str(tenant_id), now.isoformat())).fetchall()
        return [self._decode(row) for row in rows]

    def list_dispatchable(self, *, tenant_id: str, now=None, limit: int = 100):
        now = now or datetime.now(timezone.utc)
        limit = max(1, min(100, int(limit)))
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operational_notification_attempts WHERE tenant_id=? AND status IN ('pending','retry_scheduled') AND (next_attempt_at IS NULL OR next_attempt_at<=?) ORDER BY attempted_at, rowid LIMIT ?", (str(tenant_id), now.isoformat(), limit)).fetchall()
        return [self._decode(row) for row in rows]
