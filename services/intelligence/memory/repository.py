"""Tenant-scoped SQLite persistence for investigation memory and feedback."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection
from database.portability import execute_script, table_columns

from .models import AnalystFeedbackRecord, InvestigationMemoryRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class InvestigationMemoryRepository:
    """Durable memory boundary with mandatory tenant predicates on reads."""

    def __init__(self, database: str | Path | DatabaseBackend = ":memory:") -> None:
        self.db = database if hasattr(database, "connect") else DatabaseConnection(database)
        self.database = str(getattr(self.db, "database_path", database))
        self._connection = self.db.connect()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        execute_script(
            self._connection,
            """
            CREATE TABLE IF NOT EXISTS investigation_memory (
                memory_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                case_id TEXT NOT NULL,
                investigation_id TEXT NOT NULL DEFAULT '',
                investigation_type TEXT NOT NULL,
                scenario TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_summary TEXT NOT NULL DEFAULT '{}',
                reasoning_summary TEXT NOT NULL DEFAULT '{}',
                mitre_techniques TEXT NOT NULL DEFAULT '[]',
                outcome TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                synthetic_only INTEGER NOT NULL DEFAULT 1 CHECK (synthetic_only IN (0, 1)),
                provenance TEXT NOT NULL DEFAULT '{}',
                verdict TEXT NOT NULL DEFAULT '',
                attack_pattern TEXT NOT NULL DEFAULT '[]',
                evidence_fingerprint TEXT NOT NULL DEFAULT '',
                validation_result TEXT NOT NULL DEFAULT 'validated',
                audit_hash TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS investigation_memory_feedback (
                feedback_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                investigation_id TEXT NOT NULL,
                analyst_id TEXT NOT NULL,
                verdict TEXT NOT NULL,
                confidence REAL,
                reason TEXT NOT NULL DEFAULT '',
                evidence_references TEXT NOT NULL DEFAULT '[]',
                provenance TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                audit_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_investigation_memory_feedback_tenant
                ON investigation_memory_feedback(tenant_id, investigation_id, created_at);
            CREATE TABLE IF NOT EXISTS investigation_memory_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_investigation_memory_audit_tenant
                ON investigation_memory_audit(tenant_id, created_at);
            """
        )
        columns = table_columns(self._connection, self.db.backend_name, "investigation_memory")
        additions = {
            "tenant_id": "ALTER TABLE investigation_memory ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'",
            "investigation_id": "ALTER TABLE investigation_memory ADD COLUMN investigation_id TEXT NOT NULL DEFAULT ''",
            "provenance": "ALTER TABLE investigation_memory ADD COLUMN provenance TEXT NOT NULL DEFAULT '{}'",
            "verdict": "ALTER TABLE investigation_memory ADD COLUMN verdict TEXT NOT NULL DEFAULT ''",
            "attack_pattern": "ALTER TABLE investigation_memory ADD COLUMN attack_pattern TEXT NOT NULL DEFAULT '[]'",
            "evidence_fingerprint": "ALTER TABLE investigation_memory ADD COLUMN evidence_fingerprint TEXT NOT NULL DEFAULT ''",
            "validation_result": "ALTER TABLE investigation_memory ADD COLUMN validation_result TEXT NOT NULL DEFAULT 'validated'",
            "audit_hash": "ALTER TABLE investigation_memory ADD COLUMN audit_hash TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in additions.items():
            if column not in columns:
                self._connection.execute(statement)
        execute_script(
            self._connection,
            """
            CREATE INDEX IF NOT EXISTS idx_investigation_memory_tenant_case
                ON investigation_memory(tenant_id, case_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_investigation_memory_tenant_type
                ON investigation_memory(tenant_id, investigation_type, created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_investigation_memory_tenant_fingerprint
                ON investigation_memory(tenant_id, evidence_fingerprint)
                WHERE evidence_fingerprint <> '';
            """
        )
        self._connection.commit()

    @staticmethod
    def _audit_hash(payload: dict[str, Any]) -> str:
        return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()

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
        event_hash = self._audit_hash(payload)
        audit_id = hashlib.sha256(
            f"{tenant_id}|{resource_type}|{resource_id}|{event_type}|{event_hash}".encode()
        ).hexdigest()[:32]
        self._connection.execute(
            """INSERT INTO investigation_memory_audit
               (audit_id, tenant_id, resource_type, resource_id, event_type, payload, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (audit_id) DO NOTHING""",
            (audit_id, tenant_id, resource_type, resource_id, event_type, _json(payload), event_hash, created_at),
        )
        return event_hash

    def save(self, record: InvestigationMemoryRecord) -> InvestigationMemoryRecord:
        tenant_id = str(record.tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("memory_tenant_id_required")
        payload = record.to_dict()
        audit_hash = record.audit_hash or self._audit_hash(payload)
        self._connection.execute(
            """INSERT INTO investigation_memory
            (memory_id, tenant_id, case_id, investigation_id, investigation_type, scenario,
             risk_level, confidence, evidence_summary, reasoning_summary, mitre_techniques,
             outcome, created_at, synthetic_only, provenance, verdict, attack_pattern,
             evidence_fingerprint, validation_result, audit_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (memory_id) DO NOTHING""",
            (
                record.memory_id, tenant_id, record.case_id, record.investigation_id,
                record.investigation_type, record.scenario, record.risk_level,
                record.confidence, _json(record.evidence_summary), _json(record.reasoning_summary),
                _json(record.mitre_techniques), _json(record.outcome), record.created_at or _now(),
                int(record.synthetic_only), _json(record.provenance), record.verdict,
                _json(record.attack_pattern), record.evidence_fingerprint,
                record.validation_result, audit_hash,
            ),
        )
        self._append_audit(
            tenant_id=tenant_id,
            resource_type="investigation_memory",
            resource_id=record.memory_id,
            event_type="memory_stored",
            payload={"memory_id": record.memory_id, "record_hash": audit_hash},
            created_at=record.created_at or _now(),
        )
        self._connection.commit()
        return self.get(tenant_id, record.memory_id) or record

    @staticmethod
    def _record(row: Any) -> InvestigationMemoryRecord:
        data = dict(row)
        for key in ("evidence_summary", "reasoning_summary", "mitre_techniques", "outcome", "provenance", "attack_pattern"):
            default = "[]" if key in {"mitre_techniques", "attack_pattern"} else "{}"
            data[key] = json.loads(data.get(key) or default)
        data["synthetic_only"] = bool(data["synthetic_only"])
        return InvestigationMemoryRecord(**data)

    def get(self, tenant_id: str, memory_id: str) -> InvestigationMemoryRecord | None:
        row = self._connection.execute(
            "SELECT * FROM investigation_memory WHERE tenant_id=? AND memory_id=?",
            (str(tenant_id), str(memory_id)),
        ).fetchone()
        return self._record(row) if row else None

    def get_case_history(self, tenant_id: str, case_id: str | None = None, *, limit: int = 100) -> list[InvestigationMemoryRecord]:
        if case_id is None:
            case_id, tenant_id = tenant_id, "default"
        rows = self._connection.execute(
            "SELECT * FROM investigation_memory WHERE tenant_id=? AND case_id=? ORDER BY created_at, memory_id LIMIT ?",
            (str(tenant_id), str(case_id), max(1, int(limit))),
        ).fetchall()
        return [self._record(row) for row in rows]

    def find_similar(self, investigation_type: str, scenario: str = "", *, tenant_id: str = "default", limit: int = 100) -> list[InvestigationMemoryRecord]:
        rows = self._connection.execute(
            """SELECT * FROM investigation_memory
               WHERE tenant_id=? AND investigation_type=? AND (?='' OR scenario=?)
               ORDER BY created_at DESC, memory_id DESC LIMIT ?""",
            (str(tenant_id), str(investigation_type), str(scenario), str(scenario), max(1, int(limit))),
        ).fetchall()
        return [self._record(row) for row in rows]

    def all(self, tenant_id: str = "default") -> list[InvestigationMemoryRecord]:
        rows = self._connection.execute(
            "SELECT * FROM investigation_memory WHERE tenant_id=? ORDER BY created_at DESC, memory_id DESC",
            (str(tenant_id),),
        ).fetchall()
        return [self._record(row) for row in rows]

    def save_feedback(self, record: AnalystFeedbackRecord) -> AnalystFeedbackRecord:
        tenant_id = str(record.tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("memory_feedback_tenant_id_required")
        payload = record.to_dict()
        audit_hash = record.audit_hash or self._audit_hash(payload)
        self._connection.execute(
            """INSERT INTO investigation_memory_feedback
            (feedback_id, tenant_id, investigation_id, analyst_id, verdict, confidence,
             reason, evidence_references, provenance, created_at, audit_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.feedback_id, tenant_id, record.investigation_id, record.analyst_id,
             record.verdict, record.confidence, record.reason, _json(record.evidence_references),
             _json(record.provenance), record.created_at or _now(), audit_hash),
        )
        self._append_audit(
            tenant_id=tenant_id,
            resource_type="investigation_memory_feedback",
            resource_id=record.feedback_id,
            event_type="analyst_feedback_recorded",
            payload={"feedback_id": record.feedback_id, "record_hash": audit_hash},
            created_at=record.created_at or _now(),
        )
        self._connection.commit()
        return record

    def list_feedback(self, tenant_id: str, investigation_id: str | None = None) -> list[AnalystFeedbackRecord]:
        query = "SELECT * FROM investigation_memory_feedback WHERE tenant_id=?"
        parameters: list[Any] = [str(tenant_id)]
        if investigation_id is not None:
            query += " AND investigation_id=?"
            parameters.append(str(investigation_id))
        query += " ORDER BY created_at, feedback_id"
        rows = self._connection.execute(query, parameters).fetchall()
        return [
            AnalystFeedbackRecord(
                feedback_id=row["feedback_id"], tenant_id=row["tenant_id"],
                investigation_id=row["investigation_id"], analyst_id=row["analyst_id"],
                verdict=row["verdict"], confidence=row["confidence"], reason=row["reason"],
                evidence_references=json.loads(row["evidence_references"] or "[]"),
                provenance=json.loads(row["provenance"] or "{}"), created_at=row["created_at"],
                audit_hash=row["audit_hash"],
            )
            for row in rows
        ]

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM investigation_memory_audit WHERE tenant_id=? ORDER BY created_at, audit_id",
            (str(tenant_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._connection.close()
