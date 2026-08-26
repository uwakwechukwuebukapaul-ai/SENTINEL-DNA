"""Tenant-scoped append-only persistence for organizational cyber memory."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection
from database.portability import append_only_statements, execute_script

from .organizational_models import ORGANIZATIONAL_MEMORY_TYPES, OrganizationalMemoryRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class OrganizationalMemoryRepository:
    """SQLite boundary with mandatory tenant predicates and immutable records."""

    def __init__(self, database: str | Path | DatabaseBackend = ":memory:") -> None:
        self.db = database if hasattr(database, "connect") else DatabaseConnection(database)
        self.database = str(getattr(self.db, "database_path", database))
        self._connection = self.db.connect()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        execute_script(
            self._connection,
            """
            CREATE TABLE IF NOT EXISTS organizational_memory (
                record_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source_investigation_id TEXT NOT NULL,
                created_by TEXT,
                confidence REAL NOT NULL,
                observed_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                why_stored TEXT NOT NULL,
                evidence_provenance TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                audit_hash TEXT NOT NULL,
                advisory_only INTEGER NOT NULL DEFAULT 1 CHECK (advisory_only IN (0, 1))
            );
            CREATE INDEX IF NOT EXISTS idx_org_memory_tenant_type
                ON organizational_memory(tenant_id, memory_type, created_at, record_id);
            CREATE INDEX IF NOT EXISTS idx_org_memory_tenant_investigation
                ON organizational_memory(tenant_id, source_investigation_id, created_at);
            CREATE TABLE IF NOT EXISTS organizational_memory_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_org_memory_audit_tenant
                ON organizational_memory_audit(tenant_id, created_at, audit_id);
            """
        )
        for statement in append_only_statements(
            self.db.backend_name,
            table_name="organizational_memory",
            trigger_prefix="organizational_memory_append_only",
            error_message="organizational_memory_is_append_only",
        ) + append_only_statements(
            self.db.backend_name,
            table_name="organizational_memory_audit",
            trigger_prefix="organizational_memory_audit_append_only",
            error_message="organizational_memory_audit_is_append_only",
        ):
            self._connection.execute(statement)
        self._connection.commit()

    @staticmethod
    def _record_id(data: dict[str, Any]) -> str:
        for key in ("pattern_id", "campaign_id", "knowledge_id", "detection_id", "playbook_memory_id"):
            if data.get(key):
                return str(data[key])
        raise ValueError("organizational_memory_record_id_required")

    @staticmethod
    def _audit_hash(data: dict[str, Any]) -> str:
        canonical = dict(data)
        canonical.pop("audit_hash", None)
        canonical.pop("memory_type", None)
        return hashlib.sha256(_json(canonical).encode("utf-8")).hexdigest()

    def _append_audit(
        self,
        *,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> str:
        event_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
        audit_id = hashlib.sha256(
            f"{tenant_id}|{resource_type}|{resource_id}|{event_type}|{event_hash}".encode("utf-8")
        ).hexdigest()[:32]
        self._connection.execute(
            """INSERT INTO organizational_memory_audit
               (audit_id, tenant_id, resource_type, resource_id, event_type, payload, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (audit_id) DO NOTHING""",
            (audit_id, tenant_id, resource_type, resource_id, event_type, _json(payload), event_hash, created_at),
        )
        return event_hash

    def save(self, record: OrganizationalMemoryRecord) -> OrganizationalMemoryRecord:
        tenant_id = str(getattr(record, "tenant_id", "") or "").strip()
        if not tenant_id:
            raise ValueError("organizational_memory_tenant_id_required")
        data = record.to_dict()
        record_id = self._record_id(data)
        memory_type = str(data.get("memory_type") or getattr(record, "memory_type", ""))
        if memory_type not in ORGANIZATIONAL_MEMORY_TYPES:
            raise ValueError("organizational_memory_type_invalid")
        audit_hash = str(data.get("audit_hash") or self._audit_hash(data))
        data["audit_hash"] = audit_hash
        created_at = str(data.get("created_at") or _now())
        self._connection.execute(
            """INSERT INTO organizational_memory
            (record_id, tenant_id, memory_type, source_investigation_id, created_by,
             confidence, observed_at, created_at, why_stored, evidence_provenance,
             payload_json, audit_hash, advisory_only)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (record_id) DO NOTHING""",
            (
                record_id, tenant_id, memory_type, str(data.get("source_investigation_id") or ""),
                data.get("created_by"), float(data.get("confidence") or 0.0),
                str(data.get("observed_at") or created_at), created_at,
                str(data.get("why_stored") or ""), _json(data.get("evidence_provenance") or {}),
                _json(data), audit_hash, int(bool(data.get("advisory_only", True))),
            ),
        )
        self._append_audit(
            tenant_id=tenant_id,
            resource_type=memory_type,
            resource_id=record_id,
            event_type="organizational_memory_stored",
            payload={"record_id": record_id, "memory_type": memory_type, "audit_hash": audit_hash},
            created_at=created_at,
        )
        self._connection.commit()
        return self.get(tenant_id, record_id) or record

    def _from_row(self, row: Any) -> OrganizationalMemoryRecord:
        data = json.loads(row["payload_json"] or "{}")
        memory_type = str(row["memory_type"])
        data.pop("memory_type", None)
        data["audit_hash"] = str(row["audit_hash"])
        data["advisory_only"] = bool(row["advisory_only"])
        return ORGANIZATIONAL_MEMORY_TYPES[memory_type](**data)

    def get(self, tenant_id: str, record_id: str) -> OrganizationalMemoryRecord | None:
        row = self._connection.execute(
            "SELECT * FROM organizational_memory WHERE tenant_id=? AND record_id=?",
            (str(tenant_id), str(record_id)),
        ).fetchone()
        return self._from_row(row) if row else None

    def list(
        self,
        tenant_id: str,
        *,
        memory_type: str | None = None,
        source_investigation_id: str | None = None,
        limit: int = 100,
    ) -> list[OrganizationalMemoryRecord]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("organizational_memory_tenant_id_required")
        query = "SELECT * FROM organizational_memory WHERE tenant_id=?"
        params: list[Any] = [tenant_id]
        if memory_type:
            if str(memory_type) not in ORGANIZATIONAL_MEMORY_TYPES:
                raise ValueError("organizational_memory_type_invalid")
            query += " AND memory_type=?"
            params.append(str(memory_type))
        if source_investigation_id:
            query += " AND source_investigation_id=?"
            params.append(str(source_investigation_id))
        query += " ORDER BY created_at DESC, record_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 500)))
        rows = self._connection.execute(query, tuple(params)).fetchall()
        return [self._from_row(row) for row in rows]

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        if not str(tenant_id or "").strip():
            raise ValueError("organizational_memory_tenant_id_required")
        rows = self._connection.execute(
            "SELECT * FROM organizational_memory_audit WHERE tenant_id=? ORDER BY created_at, audit_id",
            (str(tenant_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._connection.close()


__all__ = ["OrganizationalMemoryRepository"]
