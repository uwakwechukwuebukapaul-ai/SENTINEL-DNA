"""Durable, tenant-scoped operations evaluation jobs and leases."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class OperationsEvaluationRepository:
    STATUSES = {"queued", "leased", "running", "completed", "failed", "cancelled", "retrying", "retry_scheduled", "dead_lettered"}

    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operations_evaluation_runs (
                evaluation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, started_at TEXT NOT NULL,
                completed_at TEXT, policies_checked INTEGER NOT NULL, alerts_created INTEGER NOT NULL,
                status TEXT NOT NULL, run_json TEXT NOT NULL,
                policy_refs_json TEXT NOT NULL DEFAULT '[]', initiator TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0, failure_json TEXT,
                completion_summary_json TEXT, lease_id TEXT, worker_id TEXT,
                acquired_at TEXT, expires_at TEXT, released_at TEXT)""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(operations_evaluation_runs)").fetchall()}
            for name, definition in (("policy_refs_json", "TEXT NOT NULL DEFAULT '[]'"), ("initiator", "TEXT"), ("retry_count", "INTEGER NOT NULL DEFAULT 0"), ("failure_json", "TEXT"), ("completion_summary_json", "TEXT"), ("lease_id", "TEXT"), ("worker_id", "TEXT"), ("acquired_at", "TEXT"), ("expires_at", "TEXT"), ("released_at", "TEXT"), ("next_attempt_at", "TEXT"), ("attempt_history_json", "TEXT NOT NULL DEFAULT '[]'")):
                if name not in columns:
                    connection.execute(f"ALTER TABLE operations_evaluation_runs ADD COLUMN {name} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operations_evaluation_tenant ON operations_evaluation_runs(tenant_id, started_at)")

    def append(self, *, tenant_id: str, status: str = "queued", policies_checked: int = 0, alerts_created: int = 0, started_at: str | None = None, completed_at: str | None = None, evaluation_id: str | None = None, policy_refs=None, initiator: str | None = None, retry_count: int = 0, failure=None, completion_summary=None, next_attempt_at: str | None = None, attempt_history=None):
        if status not in self.STATUSES: raise ValueError("invalid_operations_evaluation_status")
        event = {"evaluation_id": evaluation_id or f"OEV-{uuid4().hex}", "tenant_id": str(tenant_id), "started_at": started_at or datetime.now(timezone.utc).isoformat(), "completed_at": completed_at, "policies_checked": int(policies_checked), "alerts_created": int(alerts_created), "status": status, "policy_refs": list(policy_refs or []), "initiator": initiator or "system", "retry_count": int(retry_count), "failure": failure, "completion_summary": completion_summary, "lease_id": None, "worker_id": None, "acquired_at": None, "expires_at": None, "released_at": None, "next_attempt_at": next_attempt_at, "attempt_history": list(attempt_history or [])}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operations_evaluation_runs(evaluation_id, tenant_id, started_at, completed_at, policies_checked, alerts_created, status, run_json, policy_refs_json, initiator, retry_count, failure_json, completion_summary_json, next_attempt_at, attempt_history_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event["evaluation_id"], event["tenant_id"], event["started_at"], event["completed_at"], event["policies_checked"], event["alerts_created"], status, json.dumps(event, sort_keys=True), json.dumps(event["policy_refs"]), event["initiator"], event["retry_count"], json.dumps(failure) if failure else None, json.dumps(completion_summary) if completion_summary else None, event["next_attempt_at"], json.dumps(event["attempt_history"])))
        return event

    def get(self, evaluation_id: str, *, tenant_id: str):
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM operations_evaluation_runs WHERE evaluation_id=? AND tenant_id=?", (str(evaluation_id), str(tenant_id))).fetchone()
        return self._decode(row) if row else None

    @staticmethod
    def _decode(row):
        value = json.loads(row["run_json"])
        value.setdefault("policy_refs", json.loads(row["policy_refs_json"] or "[]")); value.setdefault("initiator", row["initiator"] or "system"); value.setdefault("retry_count", row["retry_count"] or 0)
        value.setdefault("failure", json.loads(row["failure_json"]) if row["failure_json"] else None); value.setdefault("completion_summary", json.loads(row["completion_summary_json"]) if row["completion_summary_json"] else None)
        value.setdefault("next_attempt_at", row["next_attempt_at"]); value.setdefault("attempt_history", json.loads(row["attempt_history_json"] or "[]"))
        for key in ("lease_id", "worker_id", "acquired_at", "expires_at", "released_at"): value[key] = row[key]
        return value

    def update(self, evaluation_id: str, *, tenant_id: str, status: str, policies_checked: int, alerts_created: int, completed_at: str | None = None, retry_count: int | None = None, failure=None, completion_summary=None, policy_refs=None, next_attempt_at: str | None = None, attempt_history=None, lease_id: str | None = None, worker_id: str | None = None):
        if status not in self.STATUSES: raise ValueError("invalid_operations_evaluation_status")
        current = self.get(evaluation_id, tenant_id=tenant_id)
        if not current: return None
        event = {**current, "status": status, "policies_checked": int(policies_checked), "alerts_created": int(alerts_created), "completed_at": completed_at or (current.get("completed_at") if status in {"queued", "leased", "retrying", "retry_scheduled", "running"} else datetime.now(timezone.utc).isoformat()), "retry_count": int(retry_count if retry_count is not None else current.get("retry_count", 0)), "failure": failure if failure is not None else current.get("failure"), "completion_summary": completion_summary if completion_summary is not None else current.get("completion_summary"), "policy_refs": list(policy_refs if policy_refs is not None else current.get("policy_refs", [])), "next_attempt_at": next_attempt_at if next_attempt_at is not None else current.get("next_attempt_at"), "attempt_history": list(attempt_history if attempt_history is not None else current.get("attempt_history", []))}
        with self.db.session() as connection:
            params = [event["completed_at"], event["policies_checked"], event["alerts_created"], status, json.dumps(event, sort_keys=True), json.dumps(event["policy_refs"]), event["retry_count"], json.dumps(event["failure"]) if event["failure"] else None, json.dumps(event["completion_summary"]) if event["completion_summary"] else None, event["next_attempt_at"], json.dumps(event["attempt_history"]), str(evaluation_id), str(tenant_id)]
            query = "UPDATE operations_evaluation_runs SET completed_at=?, policies_checked=?, alerts_created=?, status=?, run_json=?, policy_refs_json=?, retry_count=?, failure_json=?, completion_summary_json=?, next_attempt_at=?, attempt_history_json=? WHERE evaluation_id=? AND tenant_id=?"
            if lease_id is not None: query += " AND lease_id=? AND worker_id=?"; params.extend([str(lease_id), str(worker_id)])
            cursor = connection.execute(query, params)
            if lease_id is not None and cursor.rowcount != 1:
                return None
        return event

    def acquire_lease(self, evaluation_id: str, *, tenant_id: str, worker_id: str, lease_seconds: int = 300, now=None):
        now = now or datetime.now(timezone.utc); current = self.get(evaluation_id, tenant_id=tenant_id)
        if not current: return None
        if current.get("status") in {"completed", "failed", "cancelled", "dead_lettered"}: return current
        expiry = current.get("expires_at")
        if current.get("lease_id") and expiry and datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) > now: return None
        lease_id = f"LEA-{uuid4().hex}"; expires_at = (now + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operations_evaluation_runs SET lease_id=?, worker_id=?, acquired_at=?, expires_at=?, released_at=NULL, status='leased' WHERE evaluation_id=? AND tenant_id=? AND status IN ('queued','leased','retrying','retry_scheduled') AND (next_attempt_at IS NULL OR next_attempt_at<=?) AND (lease_id IS NULL OR expires_at IS NULL OR expires_at<=?)", (lease_id, str(worker_id), now.isoformat(), expires_at, str(evaluation_id), str(tenant_id), now.isoformat(), now.isoformat()))
            if cursor.rowcount != 1: return None
        current.update({"lease_id": lease_id, "worker_id": str(worker_id), "acquired_at": now.isoformat(), "expires_at": expires_at, "released_at": None}); return current

    def renew_lease(self, evaluation_id: str, *, tenant_id: str, worker_id: str, lease_id: str, lease_seconds: int = 300, now=None):
        now = now or datetime.now(timezone.utc); expires_at = (now + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operations_evaluation_runs SET expires_at=? WHERE evaluation_id=? AND tenant_id=? AND worker_id=? AND lease_id=? AND expires_at>?", (expires_at, str(evaluation_id), str(tenant_id), str(worker_id), str(lease_id), now.isoformat()))
        return cursor.rowcount == 1

    def release_lease(self, evaluation_id: str, *, tenant_id: str, worker_id: str, lease_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE operations_evaluation_runs SET released_at=?, lease_id=NULL, worker_id=NULL, acquired_at=NULL, expires_at=NULL WHERE evaluation_id=? AND tenant_id=? AND worker_id=? AND lease_id=?", (now.isoformat(), str(evaluation_id), str(tenant_id), str(worker_id), str(lease_id)))
        return cursor.rowcount == 1

    def recover_expired_lease(self, evaluation_id: str, *, tenant_id: str, status: str, failure=None, next_attempt_at: str | None = None, now=None):
        now = now or datetime.now(timezone.utc)
        current = self.get(evaluation_id, tenant_id=tenant_id)
        if not current or not current.get("expires_at") or datetime.fromisoformat(str(current["expires_at"]).replace("Z", "+00:00")) > now:
            return None
        recovered = self.update(evaluation_id, tenant_id=tenant_id, status=status, policies_checked=current.get("policies_checked", 0), alerts_created=0, failure=failure, next_attempt_at=next_attempt_at, completed_at=None if status in {"queued", "retry_scheduled", "retrying"} else now.isoformat(), lease_id=current.get("lease_id"), worker_id=current.get("worker_id"))
        if not recovered:
            return None
        with self.db.session() as connection:
            connection.execute("UPDATE operations_evaluation_runs SET lease_id=NULL, worker_id=NULL, acquired_at=NULL, expires_at=NULL, released_at=? WHERE evaluation_id=? AND tenant_id=? AND lease_id=? AND worker_id=?", (now.isoformat(), str(evaluation_id), str(tenant_id), str(current.get("lease_id")), str(current.get("worker_id"))))
        if recovered:
            recovered.update({"lease_id": None, "worker_id": None, "released_at": now.isoformat()})
        return recovered

    def list_expired_leases(self, *, tenant_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operations_evaluation_runs WHERE tenant_id=? AND lease_id IS NOT NULL AND expires_at IS NOT NULL AND expires_at<=? ORDER BY expires_at, rowid LIMIT 100", (str(tenant_id), now.isoformat())).fetchall()
        return [self._decode(row) for row in rows]

    def list_dispatchable(self, *, tenant_id: str, now=None, limit: int = 100):
        now = now or datetime.now(timezone.utc)
        limit = max(1, min(100, int(limit)))
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operations_evaluation_runs WHERE tenant_id=? AND status IN ('queued','retrying','retry_scheduled') AND (next_attempt_at IS NULL OR next_attempt_at<=?) ORDER BY started_at, rowid LIMIT ?", (str(tenant_id), now.isoformat(), limit)).fetchall()
        return [self._decode(row) for row in rows]

    def list_for_tenant(self, *, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operations_evaluation_runs WHERE tenant_id=? ORDER BY started_at, rowid", (str(tenant_id),)).fetchall()
        return [self._decode(row) for row in rows]

    def page_for_tenant(self, *, tenant_id: str, page=1, page_size=25):
        page, page_size = int(page), int(page_size)
        if page < 1 or page_size < 1 or page_size > 100: raise ValueError("invalid_pagination")
        offset = (page - 1) * page_size
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM operations_evaluation_runs WHERE tenant_id=? ORDER BY started_at, rowid LIMIT ? OFFSET ?", (str(tenant_id), page_size, offset)).fetchall()
            total = connection.execute("SELECT COUNT(*) AS total FROM operations_evaluation_runs WHERE tenant_id=?", (str(tenant_id),)).fetchone()["total"]
        return {"items": [self._decode(row) for row in rows], "page": page, "page_size": page_size, "total": int(total), "has_next": offset + page_size < int(total)}
