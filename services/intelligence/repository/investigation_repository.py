"""Durable investigation lifecycle repository.

This repository owns SQL for the canonical investigation record.  Reports and
intelligence remain in their existing repositories; this record joins them by
investigation and case identity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .errors import RepositoryError


_SENSITIVE_KEYS = {"authorization", "authorization_capability", "token", "password", "secret", "credential", "credentials", "database_path"}


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items() if str(k).lower() not in _SENSITIVE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


class InvestigationRepository:
    """SQLite-backed lifecycle and canonical result persistence."""

    def __init__(self, db=None) -> None:
        if db is None:
            from database.connection import database
            db = database
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    tenant_id TEXT,
                    actor_id TEXT,
                    correlation_id TEXT,
                    status TEXT NOT NULL DEFAULT 'created',
                    risk_score REAL DEFAULT 0,
                    confidence_score REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    result_metadata TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    investigation_json TEXT NOT NULL DEFAULT '{}',
                    intelligence_json TEXT NOT NULL DEFAULT '{}',
                    correlation_json TEXT NOT NULL DEFAULT '{}',
                    confidence_json TEXT NOT NULL DEFAULT '{}',
                    finding_json TEXT NOT NULL DEFAULT '{}',
                    errors_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(investigations)").fetchall()}
            additions = {
                "case_id": "TEXT",
                "tenant_id": "TEXT",
                "actor_id": "TEXT",
                "correlation_id": "TEXT",
                "risk_score": "REAL DEFAULT 0",
                "confidence_score": "REAL DEFAULT 0",
                "result_metadata": "TEXT NOT NULL DEFAULT '{}'",
                "result_json": "TEXT NOT NULL DEFAULT '{}'",
            }
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE investigations ADD COLUMN {name} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_investigations_case ON investigations(case_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_investigations_tenant ON investigations(tenant_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status)")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), default=str)

    def save_lifecycle(self, *, investigation_id: str, case_id: str, tenant_id: str | None, actor_id: str | None, correlation_id: str | None, status: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
        if status not in {"created", "running", "completed", "failed"}:
            raise ValueError("invalid investigation status")
        investigation_id = str(investigation_id or "").strip()
        case_id = str(case_id or "").strip()
        if not investigation_id or not case_id:
            raise ValueError("investigation_id and case_id are required")
        result = _safe(result or {})
        now = self._now()
        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        # Test and worker runtimes may redirect the shared database after the
        # coordinator is constructed. Ensure this repository's schema exists
        # on the active connection before a lifecycle write.
        self._ensure_schema()
        with self.db.session() as connection:
            existing = connection.execute("SELECT created_at, started_at FROM investigations WHERE investigation_id=?", (investigation_id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            started_at = existing["started_at"] if existing else (now if status in {"running", "completed", "failed"} else None)
            completed_at = now if status in {"completed", "failed"} else None
            values = {
                "investigation_id": investigation_id, "case_id": case_id,
                "tenant_id": tenant_id, "actor_id": actor_id, "correlation_id": correlation_id,
                "status": status, "risk_score": self._risk(result), "confidence_score": self._confidence(result),
                "created_at": created_at, "started_at": started_at, "completed_at": completed_at,
                "updated_at": now, "result_metadata": self._json(metadata), "result_json": self._json(result),
                "investigation_json": self._json({"investigation_id": investigation_id, "case_id": case_id}),
                "intelligence_json": self._json(result.get("intelligence", {})),
                "correlation_json": self._json(result.get("correlation", {})),
                "confidence_json": self._json(result.get("confidence", {})),
                "finding_json": self._json(result.get("findings", [])), "errors_json": self._json(result.get("errors", [])),
            }
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(investigations)").fetchall()}
            values = {key: value for key, value in values.items() if key in columns}
            names = list(values)
            if existing:
                assignments = ", ".join(f"{name}=?" for name in names if name != "investigation_id")
                params = [values[name] for name in names if name != "investigation_id"] + [investigation_id]
                connection.execute(f"UPDATE investigations SET {assignments} WHERE investigation_id=?", params)
            else:
                placeholders = ", ".join("?" for _ in names)
                connection.execute(f"INSERT INTO investigations ({', '.join(names)}) VALUES ({placeholders})", [values[name] for name in names])
        return self.get(investigation_id) or {}

    @staticmethod
    def _risk(result: dict[str, Any]) -> float:
        risk = result.get("risk", {})
        value = risk.get("score", 0) if isinstance(risk, dict) else risk
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _confidence(result: dict[str, Any]) -> float:
        try:
            return float(result.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _decode(value: Any, default: Any) -> Any:
        try:
            return json.loads(value) if value else default
        except (TypeError, ValueError):
            return default

    def get(self, investigation_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        if not investigation_id:
            return None
        with self.db.session() as connection:
            if tenant_id:
                row = connection.execute("SELECT * FROM investigations WHERE investigation_id=? AND tenant_id=?", (str(investigation_id), str(tenant_id))).fetchone()
            else:
                row = connection.execute("SELECT * FROM investigations WHERE investigation_id=?", (str(investigation_id),)).fetchone()
        if not row:
            return None
        record = dict(row)
        result = self._decode(record.get("result_json"), {})
        return {
            "investigation_id": record.get("investigation_id"), "case_id": record.get("case_id"),
            "tenant_id": record.get("tenant_id"), "actor_id": record.get("actor_id"),
            "correlation_id": record.get("correlation_id"), "status": record.get("status"),
            "risk_score": record.get("risk_score", 0), "confidence_score": record.get("confidence_score", 0),
            "created_at": record.get("created_at"), "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"), "updated_at": record.get("updated_at"),
            "result_metadata": self._decode(record.get("result_metadata"), {}), "result": result,
        }

    def get_by_case_id(self, case_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        with self.db.session() as connection:
            query = "SELECT investigation_id FROM investigations WHERE case_id=?"
            params: list[Any] = [str(case_id)]
            if tenant_id:
                query += " AND tenant_id=?"
                params.append(str(tenant_id))
            query += " ORDER BY updated_at DESC LIMIT 1"
            row = connection.execute(query, params).fetchone()
        return self.get(row["investigation_id"], tenant_id) if row else None
