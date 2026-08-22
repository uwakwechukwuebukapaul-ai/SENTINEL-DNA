"""Tenant-scoped persistence for analyst execution interaction surfaces."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class InvestigationExecutionRepository:
    """Persist a redacted execution snapshot; never store raw provider secrets."""

    def __init__(self, db: Any):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_execution_snapshots (
                    execution_id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    snapshot_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_tenant_case ON investigation_execution_snapshots(tenant_id, case_id, started_at)"
            )

    @staticmethod
    def _clean(value: Any) -> Any:
        if isinstance(value, dict):
            blocked = {"token", "secret", "password", "api_key", "authorization", "credential", "raw_response"}
            return {str(k): InvestigationExecutionRepository._clean(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, (list, tuple, set)):
            return [InvestigationExecutionRepository._clean(item) for item in value]
        if hasattr(value, "to_dict"):
            return InvestigationExecutionRepository._clean(value.to_dict())
        return value

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, snapshot: dict[str, Any], *, tenant_id: str, actor_id: str | None = None) -> dict[str, Any]:
        self._ensure_schema()
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise PermissionError("execution tenant is required")
        value = self._clean(dict(snapshot))
        execution_id = str(value.get("execution_id") or f"EXE-{uuid4().hex}")
        value["execution_id"] = execution_id
        value["tenant_id"] = tenant_id
        value["actor_id"] = actor_id or value.get("actor_id")
        value.setdefault("started_at", self._now())
        value.setdefault("updated_at", self._now())
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO investigation_execution_snapshots
                (execution_id, investigation_id, case_id, tenant_id, actor_id, status, started_at, completed_at, snapshot_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    status=excluded.status, completed_at=excluded.completed_at,
                    snapshot_json=excluded.snapshot_json, actor_id=excluded.actor_id
                """,
                (execution_id, str(value.get("investigation_id") or value.get("case_id") or ""),
                 str(value.get("case_id") or ""), tenant_id, value.get("actor_id"),
                 str(value.get("status") or "unknown"), str(value["started_at"]),
                 value.get("completed_at"), json.dumps(value, sort_keys=True, default=str)),
            )
        return value

    def get(self, execution_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        self._ensure_schema()
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM investigation_execution_snapshots WHERE execution_id=? AND tenant_id=?",
                (str(execution_id), str(tenant_id)),
            ).fetchone()
        return json.loads(row["snapshot_json"]) if row else None

    def list_for_case(self, case_id: str, *, tenant_id: str) -> list[dict[str, Any]]:
        self._ensure_schema()
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM investigation_execution_snapshots WHERE case_id=? AND tenant_id=? ORDER BY started_at",
                (str(case_id), str(tenant_id)),
            ).fetchall()
        return [json.loads(row["snapshot_json"]) for row in rows]

    def list_for_tenant(self, *, tenant_id: str) -> list[dict[str, Any]]:
        """Return redacted execution snapshots owned by one tenant only."""
        self._ensure_schema()
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM investigation_execution_snapshots WHERE tenant_id=? ORDER BY started_at",
                (str(tenant_id),),
            ).fetchall()
        return [json.loads(row["snapshot_json"]) for row in rows]

    def compare(self, execution_a: str, execution_b: str, *, tenant_id: str) -> dict[str, Any] | None:
        first = self.get(execution_a, tenant_id=tenant_id)
        second = self.get(execution_b, tenant_id=tenant_id)
        if not first or not second:
            return None
        fields = ("status", "provider_states", "evidence_refs", "findings", "risk", "decision")
        differences = {
            field: {"execution_a": first.get(field), "execution_b": second.get(field)}
            for field in fields if first.get(field) != second.get(field)
        }
        return {"version": "execution-replay-comparison-v1", "execution_a": execution_a, "execution_b": execution_b, "differences": differences}
