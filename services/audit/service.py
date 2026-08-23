"""Tenant-aware, append-only audit event persistence.

The service keeps the historical ``record(event_type, case_id, user_id,
details)`` contract while adding the minimum governance fields needed for
security review and future evidence collection. Audit metadata is treated as
untrusted input: sensitive fields are redacted and values are bounded before
they reach SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from database.connection import DatabaseConnection, database


_SENSITIVE_KEY_PARTS = (
    "password", "secret", "token", "authorization", "cookie", "credential",
    "session", "bearer", "api_key", "apikey", "raw_payload", "raw_body", "provider_response",
    "evidence_payload", "prompt", "private_key",
)
_REDACTED = "[REDACTED]"
_MAX_STRING = 512
_MAX_COLLECTION = 50
_MAX_DEPTH = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, *, limit: int = _MAX_STRING) -> str | None:
    if value is None:
        return None
    return str(value)[:limit]


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    """Return bounded JSON-safe metadata with sensitive fields redacted."""
    if depth > _MAX_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_COLLECTION:
                result["[TRUNCATED]"] = True
                break
            key_text = str(key)[:128]
            result[key_text] = _REDACTED if _sensitive_key(key_text) else _sanitize(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple, set)):
        original = list(value)
        items = [_sanitize(item, depth=depth + 1) for item in original[:_MAX_COLLECTION]]
        if len(original) > _MAX_COLLECTION:
            items.append("[TRUNCATED]")
        return items
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value if not isinstance(value, str) else value[:_MAX_STRING]
    return str(value)[:_MAX_STRING]


class AuditService:
    """Persist security/governance events without creating a second audit path."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        with self.db.session() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    case_id TEXT,
                    user_id INTEGER,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(audit_events)").fetchall()}
            migrations = {
                "event_id": "ALTER TABLE audit_events ADD COLUMN event_id TEXT",
                "tenant_id": "ALTER TABLE audit_events ADD COLUMN tenant_id TEXT",
                "actor_id": "ALTER TABLE audit_events ADD COLUMN actor_id TEXT",
                "correlation_id": "ALTER TABLE audit_events ADD COLUMN correlation_id TEXT",
                "request_id": "ALTER TABLE audit_events ADD COLUMN request_id TEXT",
                "resource_type": "ALTER TABLE audit_events ADD COLUMN resource_type TEXT",
                "resource_id": "ALTER TABLE audit_events ADD COLUMN resource_id TEXT",
                "operation": "ALTER TABLE audit_events ADD COLUMN operation TEXT",
                "outcome": "ALTER TABLE audit_events ADD COLUMN outcome TEXT",
                "latency_ms": "ALTER TABLE audit_events ADD COLUMN latency_ms REAL",
                "schema_version": "ALTER TABLE audit_events ADD COLUMN schema_version TEXT NOT NULL DEFAULT 'audit-event-v1'",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute("UPDATE audit_events SET event_id='legacy-' || id WHERE event_id IS NULL OR event_id=''")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_events_event_id ON audit_events(event_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_created ON audit_events(tenant_id, created_at, id)")
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS audit_events_append_only_update
                BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events_are_append_only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS audit_events_append_only_delete
                BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events_are_append_only'); END"""
            )

    @staticmethod
    def _request_context() -> dict[str, str | None]:
        """Best-effort trusted request enrichment; never trusts a tenant header."""
        try:
            from flask import has_request_context, request
            if not has_request_context():
                return {}
            from services.core.security_context import request_context
            context = request_context()
            return {
                "tenant_id": context.tenant_id,
                "actor_id": context.actor_id,
                "correlation_id": context.correlation_id,
                "request_id": request.headers.get("X-Request-ID"),
            }
        except Exception:
            return {}

    def record(
        self,
        event_type: str,
        case_id: str | None = None,
        user_id: int | None = None,
        details: dict[str, Any] | None = None,
        connection: Any | None = None,
        *,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        operation: str | None = None,
        outcome: str | None = None,
        latency_ms: float | int | None = None,
        metadata: dict[str, Any] | None = None,
        **extra: Any,
    ) -> str:
        context = self._request_context()
        tenant_id = tenant_id or context.get("tenant_id")
        actor_id = actor_id or context.get("actor_id")
        correlation_id = correlation_id or context.get("correlation_id")
        request_id = request_id or context.get("request_id")
        payload: dict[str, Any] = dict(details or {})
        payload.update(metadata or {})
        payload.update(extra)
        event_id = str(uuid4())
        values = (
            event_id, _safe_text(event_type, limit=128) or "unknown", _safe_text(case_id, limit=128), user_id,
            json.dumps(_sanitize(payload), sort_keys=True, separators=(",", ":")), _now(),
            _safe_text(tenant_id, limit=128), _safe_text(actor_id, limit=128),
            _safe_text(correlation_id, limit=128), _safe_text(request_id, limit=128),
            _safe_text(resource_type, limit=128), _safe_text(resource_id, limit=256),
            _safe_text(operation, limit=128), _safe_text(outcome, limit=64),
            float(latency_ms) if latency_ms is not None else None, "audit-event-v1",
        )
        statement = """INSERT INTO audit_events
            (event_id,event_type,case_id,user_id,details_json,created_at,
             tenant_id,actor_id,correlation_id,request_id,resource_type,
             resource_id,operation,outcome,latency_ms,schema_version)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        if connection is not None:
            connection.execute(statement, values)
        else:
            with self.db.session() as session:
                session.execute(statement, values)
        return event_id

    def list_for_tenant(self, tenant_id: str, *, event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not tenant_id:
            return []
        bounded_limit = max(1, min(int(limit), 500))
        query = "SELECT * FROM audit_events WHERE tenant_id=?"
        params: list[Any] = [str(tenant_id)]
        if event_type:
            query += " AND event_type=?"
            params.append(str(event_type))
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(bounded_limit)
        with self.db.session() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row(row) for row in rows]

    def get_for_tenant(self, event_id: str, tenant_id: str) -> dict[str, Any] | None:
        if not event_id or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM audit_events WHERE event_id=? AND tenant_id=?", (str(event_id), str(tenant_id))).fetchone()
        return self._row(row) if row else None

    @classmethod
    def public_event(cls, event: dict[str, Any]) -> dict[str, Any]:
        """Return the stable, secret-free HTTP projection of one event."""
        fields = (
            "event_id", "event_type", "case_id", "user_id", "created_at",
            "tenant_id", "actor_id", "correlation_id", "request_id",
            "resource_type", "resource_id", "operation", "outcome",
            "latency_ms", "schema_version",
        )
        result = {field: event.get(field) for field in fields if field in event}
        result["details"] = cls._public_details(event.get("details") or {})
        return result

    @classmethod
    def _public_details(cls, value: Any, *, depth: int = 0) -> Any:
        """Omit sensitive metadata keys from an externally readable event."""
        if depth > _MAX_DEPTH:
            return "[TRUNCATED]"
        if isinstance(value, dict):
            return {
                str(key)[:128]: cls._public_details(item, depth=depth + 1)
                for key, item in value.items()
                if not _sensitive_key(key)
            }
        if isinstance(value, (list, tuple, set)):
            return [cls._public_details(item, depth=depth + 1) for item in list(value)[:_MAX_COLLECTION]]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value if not isinstance(value, str) else value[:_MAX_STRING]
        return str(value)[:_MAX_STRING]

    @staticmethod
    def _row(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["details"] = json.loads(item.pop("details_json") or "{}")
        return item


__all__ = ["AuditService"]
