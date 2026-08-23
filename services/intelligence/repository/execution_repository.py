"""Tenant-scoped persistence for operational investigation executions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from database.connection import database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _safe_error(value: Any) -> str:
    text = str(value or "")
    return text[:256]


class ExecutionConflictError(ValueError):
    """The execution identity is already owned by another durable record."""


class InvalidExecutionTransition(ValueError):
    """A durable execution attempted an invalid state transition."""


_TERMINAL_STATES = {"COMPLETED", "FAILED", "UNAVAILABLE", "BLOCKED"}
_ALLOWED_TRANSITIONS = {
    "PENDING": {"PENDING", "QUEUED", "RUNNING", *_TERMINAL_STATES},
    "QUEUED": {"QUEUED", "RUNNING", *_TERMINAL_STATES},
    "RUNNING": {"RUNNING", *_TERMINAL_STATES},
    "COMPLETED": {"COMPLETED"},
    "FAILED": {"FAILED"},
    "UNAVAILABLE": {"UNAVAILABLE"},
    "BLOCKED": {"BLOCKED"},
}


@dataclass
class ExecutionEnvelope:
    execution_id: str
    tenant_id: str
    actor_id: str | None
    investigation_id: str
    alert_reference: str
    status: str = "PENDING"
    task_states: list[dict[str, Any]] = field(default_factory=list)
    provider_states: list[dict[str, Any]] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=_now)
    completed_at: str | None = None
    failures: list[dict[str, Any]] = field(default_factory=list)
    unavailable_reasons: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=_now)
    created_at: str | None = None
    queued_at: str | None = None
    correlation_id: str | None = None
    state_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "investigation_id": self.investigation_id,
            "alert_reference": self.alert_reference,
            "status": self.status,
            "task_states": list(self.task_states),
            "provider_states": list(self.provider_states),
            "evidence_references": list(self.evidence_references),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failures": list(self.failures),
            "unavailable_reasons": list(self.unavailable_reasons),
            "updated_at": self.updated_at,
            "created_at": self.created_at or self.started_at,
            "queued_at": self.queued_at or self.started_at,
            "correlation_id": self.correlation_id,
            "state_history": list(self.state_history),
        }


class ExecutionRepository:
    """Small synchronous repository with a worker-compatible record shape."""

    def __init__(self, db=None):
        self.db = db or database
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_execution_envelopes (
                    execution_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT,
                    investigation_id TEXT NOT NULL,
                    alert_reference TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_states_json TEXT NOT NULL,
                    provider_states_json TEXT NOT NULL,
                    evidence_references_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    failures_json TEXT NOT NULL,
                    unavailable_reasons_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_at TEXT,
                    queued_at TEXT,
                    correlation_id TEXT,
                    state_history_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(investigation_execution_envelopes)"
                ).fetchall()
            }
            migrations = {
                "created_at": "ALTER TABLE investigation_execution_envelopes ADD COLUMN created_at TEXT",
                "queued_at": "ALTER TABLE investigation_execution_envelopes ADD COLUMN queued_at TEXT",
                "correlation_id": "ALTER TABLE investigation_execution_envelopes ADD COLUMN correlation_id TEXT",
                "state_history_json": "ALTER TABLE investigation_execution_envelopes ADD COLUMN state_history_json TEXT NOT NULL DEFAULT '[]'",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_envelopes_tenant_investigation "
                "ON investigation_execution_envelopes(tenant_id, investigation_id, execution_id)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_provider_health_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    health_status TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    latency_ms REAL,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    availability_state TEXT NOT NULL,
                    policy_decision TEXT NOT NULL,
                    unavailable_reason TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_health_tenant_execution "
                "ON investigation_provider_health_snapshots(tenant_id, execution_id, provider_name)"
            )

    def save(self, envelope: ExecutionEnvelope, *, create_only: bool = False) -> ExecutionEnvelope:
        if not envelope.tenant_id or not envelope.investigation_id or not envelope.execution_id:
            raise ValueError("tenant, investigation, and execution identity are required")
        envelope.status = str(envelope.status or "PENDING").upper()
        if envelope.status not in _ALLOWED_TRANSITIONS:
            raise ValueError(f"unsupported execution state: {envelope.status}")
        envelope.updated_at = _now()
        payload = envelope.to_dict()
        with self.db.session() as connection:
            if create_only:
                connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT tenant_id, investigation_id, status FROM investigation_execution_envelopes WHERE execution_id=?",
                (envelope.execution_id,),
            ).fetchone()
            if existing is not None:
                if create_only:
                    raise ExecutionConflictError("execution already exists")
                if existing["tenant_id"] != envelope.tenant_id or existing["investigation_id"] != envelope.investigation_id:
                    raise ExecutionConflictError("execution identity is already bound to another tenant or investigation")
                current_status = str(existing["status"] or "PENDING").upper()
                if envelope.status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
                    raise InvalidExecutionTransition(f"cannot transition execution from {current_status} to {envelope.status}")
            connection.execute(
                """
                INSERT INTO investigation_execution_envelopes
                (execution_id, tenant_id, actor_id, investigation_id, alert_reference,
                 status, task_states_json, provider_states_json, evidence_references_json,
                 started_at, completed_at, failures_json, unavailable_reasons_json,
                 updated_at, created_at, queued_at, correlation_id, state_history_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    status=excluded.status, task_states_json=excluded.task_states_json,
                    provider_states_json=excluded.provider_states_json,
                    evidence_references_json=excluded.evidence_references_json,
                    completed_at=excluded.completed_at, failures_json=excluded.failures_json,
                    unavailable_reasons_json=excluded.unavailable_reasons_json,
                    updated_at=excluded.updated_at, created_at=excluded.created_at,
                    queued_at=excluded.queued_at, correlation_id=excluded.correlation_id,
                    state_history_json=excluded.state_history_json
                """,
                (
                    envelope.execution_id, envelope.tenant_id, envelope.actor_id,
                    envelope.investigation_id, envelope.alert_reference, envelope.status,
                    _json(envelope.task_states), _json(envelope.provider_states),
                    _json(envelope.evidence_references), envelope.started_at,
                    envelope.completed_at, _json(envelope.failures),
                    _json(envelope.unavailable_reasons), envelope.updated_at,
                    payload["created_at"], payload["queued_at"], envelope.correlation_id,
                    _json(envelope.state_history),
                ),
            )
        return envelope

    def create(self, envelope: ExecutionEnvelope) -> ExecutionEnvelope:
        """Create an execution exactly once; never overwrite an existing ID."""
        return self.save(envelope, create_only=True)

    def save_provider_health(self, *, execution_id: str, tenant_id: str, snapshots: list[Mapping[str, Any]]) -> None:
        with self.db.session() as connection:
            for item in snapshots:
                provider = str(item.get("provider") or item.get("provider_name") or "unknown")[:128]
                connection.execute(
                    """
                    INSERT INTO investigation_provider_health_snapshots
                    (snapshot_id, execution_id, tenant_id, provider_name, health_status,
                     checked_at, latency_ms, failure_count, availability_state,
                     policy_decision, unavailable_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PHS-{uuid4()}", execution_id, tenant_id, provider,
                        str(item.get("status") or "UNAVAILABLE"),
                        str(item.get("timestamp") or item.get("checked_at") or _now()),
                        item.get("latency_ms"), int(item.get("failure_count") or 0),
                        str(item.get("status") or "UNAVAILABLE"),
                        str(item.get("policy_decision") or "allowed"),
                        _safe_error(item.get("unavailable_reason")) if item.get("unavailable_reason") else None,
                    ),
                )

    def get(self, execution_id: str, tenant_id: str) -> dict[str, Any] | None:
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_execution_envelopes WHERE execution_id=? AND tenant_id=?",
                (str(execution_id), str(tenant_id)),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        return {
            "execution_id": row["execution_id"], "tenant_id": row["tenant_id"],
            "actor_id": row["actor_id"], "investigation_id": row["investigation_id"],
            "alert_reference": row["alert_reference"], "status": row["status"],
            "task_states": json.loads(row["task_states_json"]),
            "provider_states": json.loads(row["provider_states_json"]),
            "evidence_references": json.loads(row["evidence_references_json"]),
            "started_at": row["started_at"], "completed_at": row["completed_at"],
            "failures": json.loads(row["failures_json"]),
            "unavailable_reasons": json.loads(row["unavailable_reasons_json"]),
            "updated_at": row["updated_at"],
            "created_at": row["created_at"] or row["started_at"],
            "queued_at": row["queued_at"] or row["started_at"],
            "correlation_id": row["correlation_id"],
            "state_history": json.loads(row["state_history_json"] or "[]"),
        }

    def list_for_tenant(self, tenant_id: str, *, investigation_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if not tenant_id:
            return []
        bounded_limit = max(1, min(int(limit), 100))
        query = "SELECT * FROM investigation_execution_envelopes WHERE tenant_id=?"
        params: list[Any] = [str(tenant_id)]
        if investigation_id:
            query += " AND investigation_id=?"
            params.append(str(investigation_id))
        query += " ORDER BY started_at DESC, execution_id DESC LIMIT ?"
        params.append(bounded_limit)
        with self.db.session() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def provider_health_for_execution(self, execution_id: str, tenant_id: str) -> list[dict[str, Any]]:
        if not execution_id or not tenant_id:
            return []
        with self.db.session() as connection:
            rows = connection.execute(
                """
                SELECT provider_name, health_status, checked_at, latency_ms,
                       failure_count, availability_state, policy_decision,
                       unavailable_reason
                FROM investigation_provider_health_snapshots
                WHERE execution_id=? AND tenant_id=?
                ORDER BY checked_at DESC, provider_name ASC
                """,
                (str(execution_id), str(tenant_id)),
            ).fetchall()
        return [dict(row) for row in rows]

__all__ = [
    "ExecutionConflictError",
    "ExecutionEnvelope",
    "ExecutionRepository",
    "InvalidExecutionTransition",
]
