"""Tenant-scoped persistence for operational investigation executions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

from database.connection import database
from database.portability import table_columns
from services.audit.service import AuditService
from services.intelligence.investigation.canonical import sha256_digest


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


class JobConflictError(ValueError):
    """A durable job identity conflicts with an existing job."""


class JobLeaseError(ValueError):
    """A durable job lease cannot be claimed, renewed, or recovered."""


class ProviderBudgetError(ValueError):
    """A provider execution budget reservation failed closed."""


class ProviderObservationLineageError(ValueError):
    """A stored provider observation is not bound to the requested execution."""


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
        # Reuse the canonical append-only, redacting audit path.  This avoids
        # creating a second audit repository for investigation lifecycle data.
        self.audit_service = AuditService(self.db)
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
            columns = table_columns(connection, self.db.backend_name, "investigation_execution_envelopes")
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
                CREATE TABLE IF NOT EXISTS investigation_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL UNIQUE,
                    trigger_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    actor_id TEXT,
                    service_identity TEXT,
                    correlation_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    iteration INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    claimed_at TEXT,
                    lease_until TEXT,
                    heartbeat_at TEXT,
                    completed_at TEXT,
                    failure_code TEXT,
                    failure_reason TEXT,
                    snapshot_id TEXT,
                    snapshot_digest TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    state_history_json TEXT NOT NULL DEFAULT '[]',
                    UNIQUE (tenant_id, idempotency_key)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_jobs_claim "
                "ON investigation_jobs(state, available_at, lease_until, priority, created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_jobs_tenant "
                "ON investigation_jobs(tenant_id, case_id, investigation_id, created_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_triggers (
                    trigger_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    actor_id TEXT,
                    service_identity TEXT,
                    correlation_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    normalized_at TEXT,
                    authorization_result TEXT NOT NULL,
                    eligibility_result TEXT NOT NULL,
                    rejection_reason TEXT,
                    job_id TEXT,
                    payload_digest TEXT NOT NULL,
                    normalized_payload_json TEXT NOT NULL,
                    UNIQUE (tenant_id, idempotency_key)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_triggers_tenant "
                "ON investigation_triggers(tenant_id, source, source_event_id, received_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    digest TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    actor_id TEXT,
                    correlation_id TEXT,
                    iteration INTEGER NOT NULL,
                    parent_snapshot_id TEXT,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (job_id, iteration)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_snapshots_scope "
                "ON investigation_snapshots(tenant_id, case_id, investigation_id, job_id, iteration)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_snapshots_digest "
                "ON investigation_snapshots(digest)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_sufficiency_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    correlation_id TEXT,
                    iteration INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    input_evidence_digest TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (job_id, iteration)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sufficiency_scope "
                "ON investigation_sufficiency_evaluations(tenant_id, case_id, investigation_id, job_id, iteration)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_follow_up_tasks (
                    task_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    parent_task_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    required_evidence_json TEXT NOT NULL,
                    authorization_reference TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    budget_cost REAL NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    task_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (job_id, iteration)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_follow_up_tasks_scope "
                "ON investigation_follow_up_tasks(tenant_id, case_id, investigation_id, job_id, iteration)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_provider_requests (
                    request_id TEXT PRIMARY KEY,
                    request_digest TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    observation_ids_json TEXT NOT NULL DEFAULT '[]',
                    request_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigation_provider_requests_scope "
                "ON investigation_provider_requests(tenant_id, job_id, task_id, iteration)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_provider_budget_ledger (
                    ledger_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    provider_name TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    reserved_cost REAL NOT NULL,
                    consumed_cost REAL NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    reserved_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE (request_id, provider_name)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_budget_tenant "
                "ON investigation_provider_budget_ledger(tenant_id, reserved_at, provider_name)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_provider_observation_links (
                    observation_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    capability TEXT NOT NULL,
                    authorization_reference TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    PRIMARY KEY (observation_id, request_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_observation_links_scope "
                "ON investigation_provider_observation_links(tenant_id, job_id, investigation_id, request_id)"
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
            health_columns = table_columns(connection, self.db.backend_name, "investigation_provider_health_snapshots")
            health_migrations = {
                "request_id": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN request_id TEXT",
                "job_id": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN job_id TEXT",
                "task_id": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN task_id TEXT",
                "investigation_id": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN investigation_id TEXT",
                "iteration": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN iteration INTEGER",
                "correlation_id": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN correlation_id TEXT",
                "outcome": "ALTER TABLE investigation_provider_health_snapshots ADD COLUMN outcome TEXT",
            }
            for column, statement in health_migrations.items():
                if column not in health_columns:
                    connection.execute(statement)
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

    @staticmethod
    def _job_from_row(row: Any) -> InvestigationJob:
        from services.intelligence.runtime.investigation_job import InvestigationJob

        if row is None:
            raise JobConflictError("investigation job is unavailable")
        return InvestigationJob(
            job_id=row["job_id"], tenant_id=row["tenant_id"], case_id=row["case_id"],
            investigation_id=row["investigation_id"], execution_id=row["execution_id"],
            trigger_id=row["trigger_id"], idempotency_key=row["idempotency_key"],
            actor_id=row["actor_id"], service_identity=row["service_identity"],
            correlation_id=row["correlation_id"], state=row["state"], priority=row["priority"],
            attempts=row["attempts"], max_attempts=row["max_attempts"], iteration=row["iteration"],
            created_at=row["created_at"], available_at=row["available_at"],
            claimed_at=row["claimed_at"], lease_until=row["lease_until"],
            heartbeat_at=row["heartbeat_at"], completed_at=row["completed_at"],
            failure_code=row["failure_code"], failure_reason=row["failure_reason"],
            snapshot_id=row["snapshot_id"], snapshot_digest=row["snapshot_digest"],
            cancel_requested=bool(row["cancel_requested"]),
            state_history=json.loads(row["state_history_json"] or "[]"),
        )

    @staticmethod
    def _trigger_from_row(row: Any) -> Any:
        from services.intelligence.runtime.investigation_intake import InvestigationTrigger

        if row is None:
            raise JobConflictError("investigation trigger is unavailable")
        return InvestigationTrigger(
            trigger_id=row["trigger_id"], tenant_id=row["tenant_id"],
            source=row["source"], source_event_id=row["source_event_id"],
            actor_id=row["actor_id"], service_identity=row["service_identity"],
            correlation_id=row["correlation_id"], idempotency_key=row["idempotency_key"],
            received_at=row["received_at"], normalized_at=row["normalized_at"],
            authorization_result=row["authorization_result"],
            eligibility_result=row["eligibility_result"],
            rejection_reason=row["rejection_reason"], job_id=row["job_id"],
            payload_digest=row["payload_digest"],
            normalized_payload=json.loads(row["normalized_payload_json"] or "{}"),
        )

    @staticmethod
    def _next_resource_sequence(connection: Any, tenant_id: str, resource_type: str, resource_id: str) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_sequence
            FROM audit_events
            WHERE tenant_id=? AND resource_type=? AND resource_id=?
            """,
            (tenant_id, resource_type, resource_id),
        ).fetchone()
        return int(row["next_sequence"])

    def record_trigger_audit_event(
        self,
        *,
        tenant_id: str | None,
        trigger_id: str,
        event_type: str,
        actor_id: str | None = None,
        service_identity: str | None = None,
        correlation_id: str | None = None,
        case_id: str | None = None,
        investigation_id: str | None = None,
        job_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        connection: Any | None = None,
    ) -> str:
        """Record secret-safe trigger lineage in the canonical audit store."""
        if not trigger_id or not event_type:
            raise ValueError("trigger and event identity are required")
        if not actor_id and not service_identity:
            raise PermissionError("actor or service identity is required")
        payload = dict(metadata or {})
        payload.update({
            "trigger_id": trigger_id,
            "job_id": job_id,
            "service_identity": service_identity,
        })

        def write(active_connection: Any) -> str:
            if tenant_id:
                row = active_connection.execute(
                    "SELECT tenant_id FROM investigation_triggers WHERE trigger_id=?",
                    (str(trigger_id),),
                ).fetchone()
                if row is not None and str(row["tenant_id"]) != str(tenant_id):
                    raise PermissionError("trigger tenant does not match requested tenant")
                sequence = self._next_resource_sequence(
                    active_connection, str(tenant_id), "investigation_trigger", str(trigger_id)
                )
            else:
                sequence = None
            return self.audit_service.record(
                event_type,
                case_id=case_id or investigation_id,
                tenant_id=str(tenant_id) if tenant_id else None,
                actor_id=actor_id,
                correlation_id=correlation_id,
                resource_type="investigation_trigger",
                resource_id=str(trigger_id),
                operation=event_type,
                outcome="recorded",
                sequence_number=sequence,
                details=payload,
                connection=active_connection,
            )

        if connection is not None:
            return write(connection)
        with self.db.session() as active_connection:
            active_connection.execute("BEGIN IMMEDIATE")
            return write(active_connection)

    def get_trigger(self, trigger_id: str, tenant_id: str) -> Any | None:
        if not trigger_id or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_triggers WHERE trigger_id=? AND tenant_id=?",
                (str(trigger_id), str(tenant_id)),
            ).fetchone()
        return self._trigger_from_row(row) if row else None

    def get_trigger_by_idempotency_key(self, idempotency_key: str, tenant_id: str) -> Any | None:
        if not idempotency_key or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_triggers WHERE idempotency_key=? AND tenant_id=?",
                (str(idempotency_key), str(tenant_id)),
            ).fetchone()
        return self._trigger_from_row(row) if row else None

    def create_trigger(self, trigger: Any) -> tuple[Any, bool]:
        """Persist one immutable trigger, returning (record, duplicate)."""
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM investigation_triggers WHERE tenant_id=? AND idempotency_key=?",
                (trigger.tenant_id, trigger.idempotency_key),
            ).fetchone()
            if existing is not None:
                stored = self._trigger_from_row(existing)
                if stored.payload_digest != trigger.payload_digest or stored.source_event_id != trigger.source_event_id:
                    raise JobConflictError("trigger idempotency key conflicts with another alert")
                return stored, True
            connection.execute(
                """
                INSERT INTO investigation_triggers
                (trigger_id, tenant_id, source, source_event_id, actor_id,
                 service_identity, correlation_id, idempotency_key, received_at,
                 normalized_at, authorization_result, eligibility_result,
                 rejection_reason, job_id, payload_digest, normalized_payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trigger.trigger_id, trigger.tenant_id, trigger.source,
                    trigger.source_event_id, trigger.actor_id, trigger.service_identity,
                    trigger.correlation_id, trigger.idempotency_key, trigger.received_at,
                    trigger.normalized_at, trigger.authorization_result,
                    trigger.eligibility_result, trigger.rejection_reason, trigger.job_id,
                    trigger.payload_digest, _json(trigger.normalized_payload),
                ),
            )
            return trigger, False

    def create_trigger_and_job(self, trigger: Any, job: InvestigationJob) -> tuple[Any, InvestigationJob, bool]:
        """Atomically persist an eligible trigger and its queued investigation job."""
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            InvalidInvestigationTransition,
            LifecycleTransition,
            validate_transition,
        )

        if job.state != InvestigationLifecycleState.PENDING:
            raise InvalidInvestigationTransition("new investigation jobs must start in PENDING")
        if (
            trigger.tenant_id != job.tenant_id
            or trigger.trigger_id != job.trigger_id
            or trigger.idempotency_key != job.idempotency_key
            or trigger.job_id != job.job_id
            or trigger.correlation_id != job.correlation_id
        ):
            raise PermissionError("trigger and job identity do not match")
        validate_transition(None, job.state)
        created_at = job.created_at or _now()
        available_at = job.available_at or created_at
        pending = LifecycleTransition.create(
            previous_state=None, next_state=InvestigationLifecycleState.PENDING,
            tenant_id=job.tenant_id, case_id=job.case_id,
            investigation_id=job.investigation_id, execution_id=job.execution_id,
            job_id=job.job_id, actor_id=job.actor_id, service_identity=job.service_identity,
            correlation_id=job.correlation_id, reason="job created",
            attempt=job.attempts, iteration=job.iteration,
        )
        queued = LifecycleTransition.create(
            previous_state=InvestigationLifecycleState.PENDING,
            next_state=InvestigationLifecycleState.QUEUED,
            tenant_id=job.tenant_id, case_id=job.case_id,
            investigation_id=job.investigation_id, execution_id=job.execution_id,
            job_id=job.job_id, actor_id=job.actor_id, service_identity=job.service_identity,
            correlation_id=job.correlation_id, reason="eligible durable intake",
            attempt=job.attempts, iteration=job.iteration,
        )
        job.created_at = created_at
        job.available_at = available_at
        job.state = InvestigationLifecycleState.QUEUED
        job.state_history = [pending.to_dict(), queued.to_dict()]
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM investigation_triggers WHERE tenant_id=? AND idempotency_key=?",
                (trigger.tenant_id, trigger.idempotency_key),
            ).fetchone()
            if existing is not None:
                stored = self._trigger_from_row(existing)
                if stored.payload_digest != trigger.payload_digest or stored.source_event_id != trigger.source_event_id:
                    raise JobConflictError("trigger idempotency key conflicts with another alert")
                existing_job = connection.execute(
                    "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                    (stored.job_id, stored.tenant_id),
                ).fetchone()
                if existing_job is None:
                    raise JobConflictError("trigger exists without its durable job")
                return stored, self._job_from_row(existing_job), True
            connection.execute(
                """
                INSERT INTO investigation_triggers
                (trigger_id, tenant_id, source, source_event_id, actor_id,
                 service_identity, correlation_id, idempotency_key, received_at,
                 normalized_at, authorization_result, eligibility_result,
                 rejection_reason, job_id, payload_digest, normalized_payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trigger.trigger_id, trigger.tenant_id, trigger.source,
                    trigger.source_event_id, trigger.actor_id, trigger.service_identity,
                    trigger.correlation_id, trigger.idempotency_key, trigger.received_at,
                    trigger.normalized_at, trigger.authorization_result,
                    trigger.eligibility_result, trigger.rejection_reason, job.job_id,
                    trigger.payload_digest, _json(trigger.normalized_payload),
                ),
            )
            try:
                self._insert_job_locked(connection, job)
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise JobConflictError("investigation job identity already exists") from exc
                raise
            self.record_transition(pending, connection=connection)
            self.record_transition(queued, connection=connection)
            return trigger, job, False

    def _insert_job_locked(self, connection: Any, job: InvestigationJob) -> None:
        connection.execute(
            """
            INSERT INTO investigation_jobs
            (job_id, tenant_id, case_id, investigation_id, execution_id,
             trigger_id, idempotency_key, actor_id, service_identity,
             correlation_id, state, priority, attempts, max_attempts,
             iteration, created_at, available_at, claimed_at, lease_until,
             heartbeat_at, completed_at, failure_code, failure_reason,
             snapshot_id, snapshot_digest, cancel_requested, state_history_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id, job.tenant_id, job.case_id, job.investigation_id,
                job.execution_id, job.trigger_id, job.idempotency_key,
                job.actor_id, job.service_identity, job.correlation_id,
                job.state.value, job.priority, job.attempts, job.max_attempts,
                job.iteration, job.created_at, job.available_at, job.claimed_at,
                job.lease_until, job.heartbeat_at, job.completed_at,
                job.failure_code, job.failure_reason, job.snapshot_id,
                job.snapshot_digest, int(job.cancel_requested), _json(job.state_history),
            ),
        )

    @staticmethod
    def _next_audit_sequence(connection: Any, tenant_id: str, job_id: str) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_sequence
            FROM audit_events
            WHERE tenant_id=? AND resource_type=? AND resource_id=?
            """,
            (tenant_id, "investigation_job", job_id),
        ).fetchone()
        return int(row["next_sequence"])

    def record_audit_event(
        self,
        *,
        tenant_id: str,
        job_id: str,
        event_type: str,
        actor_id: str | None = None,
        service_identity: str | None = None,
        correlation_id: str | None = None,
        case_id: str | None = None,
        investigation_id: str | None = None,
        execution_id: str | None = None,
        task_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        connection: Any | None = None,
    ) -> str:
        if not tenant_id or not job_id or not event_type:
            raise ValueError("tenant, job, and event identity are required")
        if not actor_id and not service_identity:
            raise PermissionError("actor or service identity is required")
        payload = dict(metadata or {})
        payload.update({
            "job_id": job_id,
            "investigation_id": investigation_id,
            "execution_id": execution_id,
            "task_id": task_id,
            "service_identity": service_identity,
        })

        def write(active_connection: Any) -> str:
            job_row = active_connection.execute(
                """
                SELECT tenant_id, case_id, investigation_id, execution_id
                FROM investigation_jobs WHERE job_id=?
                """,
                (str(job_id),),
            ).fetchone()
            if job_row is None:
                raise ValueError("investigation job is required for audit event")
            if str(job_row["tenant_id"]) != str(tenant_id):
                raise PermissionError("audit job tenant does not match requested tenant")
            for supplied, stored, label in (
                (case_id, job_row["case_id"], "case"),
                (investigation_id, job_row["investigation_id"], "investigation"),
                (execution_id, job_row["execution_id"], "execution"),
            ):
                if supplied is not None and str(supplied) != str(stored):
                    raise PermissionError(f"audit {label} identity does not match job")
            sequence = self._next_audit_sequence(active_connection, str(tenant_id), str(job_id))
            return self.audit_service.record(
                event_type,
                case_id=case_id or investigation_id,
                tenant_id=str(tenant_id),
                actor_id=actor_id,
                correlation_id=correlation_id,
                resource_type="investigation_job",
                resource_id=str(job_id),
                operation=event_type,
                outcome="recorded",
                sequence_number=sequence,
                details=payload,
                connection=active_connection,
            )

        if connection is not None:
            return write(connection)
        with self.db.session() as active_connection:
            active_connection.execute("BEGIN IMMEDIATE")
            return write(active_connection)

    def record_transition(
        self,
        transition: LifecycleTransition,
        *,
        connection: Any | None = None,
    ) -> str:
        return self.record_audit_event(
            tenant_id=transition.tenant_id,
            job_id=transition.job_id,
            event_type="INVESTIGATION_JOB_TRANSITION",
            actor_id=transition.actor_id,
            service_identity=transition.service_identity,
            correlation_id=transition.correlation_id,
            case_id=transition.case_id,
            investigation_id=transition.investigation_id,
            execution_id=transition.execution_id,
            metadata=transition.to_dict(),
            connection=connection,
        )

    @staticmethod
    def _transition_history(job: InvestigationJob, transition: LifecycleTransition) -> list[dict[str, Any]]:
        return [*job.state_history, transition.to_dict()]

    def create_job(self, job: InvestigationJob) -> InvestigationJob:
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            InvalidInvestigationTransition,
            LifecycleTransition,
            validate_transition,
        )

        if job.state != InvestigationLifecycleState.PENDING:
            raise InvalidInvestigationTransition("new investigation jobs must start in PENDING")
        validate_transition(None, job.state)
        created_at = job.created_at or _now()
        available_at = job.available_at or created_at
        transition = LifecycleTransition.create(
            previous_state=None,
            next_state=job.state,
            tenant_id=job.tenant_id, case_id=job.case_id,
            investigation_id=job.investigation_id, execution_id=job.execution_id,
            job_id=job.job_id, actor_id=job.actor_id, service_identity=job.service_identity,
            correlation_id=job.correlation_id, reason="job created",
            attempt=job.attempts, iteration=job.iteration,
        )
        job.created_at = created_at
        job.available_at = available_at
        job.state_history = [transition.to_dict()]
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM investigation_jobs WHERE tenant_id=? AND idempotency_key=?",
                (job.tenant_id, job.idempotency_key),
            ).fetchone()
            if existing is not None:
                existing_job = self._job_from_row(existing)
                if existing_job.identity() != job.identity() or existing_job.trigger_id != job.trigger_id:
                    raise JobConflictError("idempotency key conflicts with another investigation identity")
                return existing_job
            try:
                connection.execute(
                    """
                    INSERT INTO investigation_jobs
                    (job_id, tenant_id, case_id, investigation_id, execution_id,
                     trigger_id, idempotency_key, actor_id, service_identity,
                     correlation_id, state, priority, attempts, max_attempts,
                     iteration, created_at, available_at, claimed_at, lease_until,
                     heartbeat_at, completed_at, failure_code, failure_reason,
                     snapshot_id, snapshot_digest, cancel_requested, state_history_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.job_id, job.tenant_id, job.case_id, job.investigation_id,
                        job.execution_id, job.trigger_id, job.idempotency_key,
                        job.actor_id, job.service_identity, job.correlation_id,
                        job.state.value, job.priority, job.attempts, job.max_attempts,
                        job.iteration, job.created_at, job.available_at, job.claimed_at,
                        job.lease_until, job.heartbeat_at, job.completed_at,
                        job.failure_code, job.failure_reason, job.snapshot_id,
                        job.snapshot_digest, int(job.cancel_requested),
                        _json(job.state_history),
                    ),
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise JobConflictError("investigation job identity already exists") from exc
                raise
            self.record_transition(transition, connection=connection)
        return job

    def get_job(self, job_id: str, tenant_id: str) -> InvestigationJob | None:
        if not job_id or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), str(tenant_id)),
            ).fetchone()
        return self._job_from_row(row) if row else None

    def get_job_by_idempotency_key(self, idempotency_key: str, tenant_id: str) -> InvestigationJob | None:
        if not idempotency_key or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE idempotency_key=? AND tenant_id=?",
                (str(idempotency_key), str(tenant_id)),
            ).fetchone()
        return self._job_from_row(row) if row else None

    def transition_job(
        self,
        job_id: str,
        tenant_id: str,
        next_state: InvestigationLifecycleState | str,
        *,
        actor_id: str | None = None,
        service_identity: str | None = None,
        correlation_id: str | None = None,
        reason: str = "state transition",
        attempt: int | None = None,
        iteration: int | None = None,
        recovery_authorized: bool = False,
        failure_code: str | None = None,
        failure_reason: str | None = None,
        require_lease: bool = False,
        now: str | None = None,
    ) -> InvestigationJob | None:
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            LifecycleTransition,
        )

        if not job_id or not tenant_id or (not actor_id and not service_identity):
            raise PermissionError("job, tenant, and actor or service identity are required")
        if require_lease and not service_identity:
            raise PermissionError("lease-owned transitions require service identity")
        current = now or _now()
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), str(tenant_id)),
            ).fetchone()
            if row is None:
                return None
            job = self._job_from_row(row)
            if require_lease and (
                job.state.value != "RUNNING"
                or job.service_identity != service_identity
                or not job.lease_until
                or job.lease_until <= current
            ):
                raise JobLeaseError("job lease is not owned by this service")
            effective_correlation = correlation_id or job.correlation_id
            transition = LifecycleTransition.create(
                previous_state=job.state,
                next_state=next_state,
                tenant_id=job.tenant_id, case_id=job.case_id,
                investigation_id=job.investigation_id, execution_id=job.execution_id,
                job_id=job.job_id, actor_id=actor_id, service_identity=service_identity,
                correlation_id=effective_correlation, reason=reason,
                attempt=job.attempts if attempt is None else attempt,
                iteration=job.iteration if iteration is None else iteration,
                recovery_authorized=recovery_authorized,
            )
            history = self._transition_history(job, transition)
            from services.intelligence.runtime.investigation_lifecycle import TERMINAL_STATES
            completed_at = transition.timestamp if transition.next_state in {state.value for state in TERMINAL_STATES} else job.completed_at
            lease_clause = ""
            lease_params: tuple[Any, ...] = ()
            if require_lease:
                lease_clause = " AND state=? AND service_identity=? AND lease_until>?"
                lease_params = (
                    InvestigationLifecycleState.RUNNING.value,
                    str(service_identity),
                    current,
                )
            updated = connection.execute(
                """
                UPDATE investigation_jobs
                SET state=?, completed_at=?, failure_code=?, failure_reason=?,
                    cancel_requested=?, state_history_json=?,
                    lease_until=CASE WHEN ? THEN NULL ELSE lease_until END,
                    heartbeat_at=CASE WHEN ? THEN NULL ELSE heartbeat_at END
                WHERE job_id=? AND tenant_id=?
                """ + lease_clause,
                (
                    transition.next_state, completed_at,
                    failure_code or job.failure_code,
                    (failure_reason or job.failure_reason or "")[:256] if (failure_reason or job.failure_reason) else None,
                    int(job.cancel_requested or transition.next_state == InvestigationLifecycleState.CANCELLED.value),
                    _json(history), int(require_lease), int(require_lease),
                    job.job_id, job.tenant_id, *lease_params,
                ),
            )
            if require_lease and updated.rowcount != 1:
                raise JobLeaseError("job lease was lost before finalization")
            self.record_transition(transition, connection=connection)
            refreshed = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            ).fetchone()
            return self._job_from_row(refreshed)

    def request_cancellation(
        self,
        job_id: str,
        tenant_id: str,
        *,
        actor_id: str | None = None,
        service_identity: str | None = None,
        correlation_id: str | None = None,
        reason: str = "cancellation requested",
    ) -> InvestigationJob | None:
        from services.intelligence.runtime.investigation_lifecycle import TERMINAL_STATES

        if not job_id or not tenant_id or (not actor_id and not service_identity):
            raise PermissionError("job, tenant, and actor or service identity are required")
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), str(tenant_id)),
            ).fetchone()
            if row is None:
                return None
            job = self._job_from_row(row)
            if job.state in TERMINAL_STATES:
                self.record_audit_event(
                    tenant_id=job.tenant_id, job_id=job.job_id,
                    event_type="INVESTIGATION_JOB_CANCELLATION_IGNORED",
                    actor_id=actor_id, service_identity=service_identity,
                    correlation_id=correlation_id or job.correlation_id,
                    case_id=job.case_id,
                    investigation_id=job.investigation_id, execution_id=job.execution_id,
                    metadata={"state": job.state.value, "reason": reason}, connection=connection,
                )
                return job
            if job.state.value in {
                "PENDING",
                "QUEUED",
            }:
                from services.intelligence.runtime.investigation_lifecycle import LifecycleTransition

                transition = LifecycleTransition.create(
                    previous_state=job.state,
                    next_state="CANCELLED",
                    tenant_id=job.tenant_id,
                    case_id=job.case_id,
                    investigation_id=job.investigation_id,
                    execution_id=job.execution_id,
                    job_id=job.job_id,
                    actor_id=actor_id,
                    service_identity=service_identity,
                    correlation_id=correlation_id or job.correlation_id,
                    reason=reason,
                    attempt=job.attempts,
                    iteration=job.iteration,
                )
                connection.execute(
                    """
                    UPDATE investigation_jobs
                    SET state='CANCELLED', cancel_requested=1,
                        completed_at=?, state_history_json=?
                    WHERE job_id=? AND tenant_id=?
                    """,
                    (
                        transition.timestamp,
                        _json(self._transition_history(job, transition)),
                        job.job_id,
                        job.tenant_id,
                    ),
                )
                self.record_transition(transition, connection=connection)
                row = connection.execute(
                    "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                    (job.job_id, job.tenant_id),
                ).fetchone()
                return self._job_from_row(row)
            connection.execute(
                "UPDATE investigation_jobs SET cancel_requested=1 WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            )
            self.record_audit_event(
                tenant_id=job.tenant_id, job_id=job.job_id,
                event_type="INVESTIGATION_JOB_CANCELLATION_REQUESTED",
                actor_id=actor_id, service_identity=service_identity,
                correlation_id=correlation_id or job.correlation_id,
                case_id=job.case_id,
                investigation_id=job.investigation_id, execution_id=job.execution_id,
                metadata={"state": job.state.value, "reason": reason}, connection=connection,
            )
            refreshed = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            ).fetchone()
            return self._job_from_row(refreshed)

    def get_cancellation_state(self, job_id: str, tenant_id: str) -> bool | None:
        job = self.get_job(job_id, tenant_id)
        return None if job is None else job.cancel_requested

    def claim_job(
        self,
        service_identity: str,
        *,
        tenant_id: str | None = None,
        lease_seconds: int = 60,
        now: str | None = None,
    ) -> InvestigationJob | None:
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            LifecycleTransition,
        )

        if not service_identity or int(lease_seconds) <= 0:
            raise ValueError("service identity and positive lease duration are required")
        current = now or _now()
        lease_until = (datetime.fromisoformat(current) + timedelta(seconds=int(lease_seconds))).isoformat()
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            params: list[Any] = [InvestigationLifecycleState.QUEUED.value, current, current]
            tenant_clause = ""
            if tenant_id:
                tenant_clause = " AND tenant_id=?"
                params.append(str(tenant_id))
            row = connection.execute(
                """
                SELECT * FROM investigation_jobs
                WHERE state=? AND available_at<=?
                  AND (lease_until IS NULL OR lease_until<=?)
                  AND cancel_requested=0
                """ + tenant_clause + " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, available_at, created_at, job_id LIMIT 1",
                tuple(params),
            ).fetchone()
            if row is None:
                return None
            job = self._job_from_row(row)
            transition = LifecycleTransition.create(
                previous_state=job.state, next_state=InvestigationLifecycleState.RUNNING,
                tenant_id=job.tenant_id, case_id=job.case_id,
                investigation_id=job.investigation_id, execution_id=job.execution_id,
                job_id=job.job_id, actor_id=job.actor_id, service_identity=service_identity,
                correlation_id=job.correlation_id, reason="worker claim",
                attempt=job.attempts + 1, iteration=job.iteration,
            )
            history = self._transition_history(job, transition)
            updated = connection.execute(
                """
                UPDATE investigation_jobs
                SET state=?, attempts=attempts+1, claimed_at=?, lease_until=?,
                    heartbeat_at=?, service_identity=?, state_history_json=?
                WHERE job_id=? AND state=? AND cancel_requested=0
                """,
                (transition.next_state, current, lease_until, current, service_identity,
                 _json(history), job.job_id, InvestigationLifecycleState.QUEUED.value),
            )
            if updated.rowcount != 1:
                raise JobLeaseError("job claim lost its atomic ownership")
            self.record_transition(transition, connection=connection)
            refreshed = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            ).fetchone()
            return self._job_from_row(refreshed)

    def heartbeat_job(
        self,
        job_id: str,
        tenant_id: str,
        service_identity: str,
        *,
        lease_seconds: int = 60,
        now: str | None = None,
    ) -> InvestigationJob:
        from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState

        if not job_id or not tenant_id or not service_identity or int(lease_seconds) <= 0:
            raise ValueError("job, tenant, service identity, and positive lease duration are required")
        current = now or _now()
        lease_until = (datetime.fromisoformat(current) + timedelta(seconds=int(lease_seconds))).isoformat()
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE investigation_jobs
                SET heartbeat_at=?, lease_until=?
                WHERE job_id=? AND tenant_id=? AND state=?
                  AND service_identity=? AND (lease_until IS NULL OR lease_until>?)
                """,
                (current, lease_until, job_id, tenant_id,
                 InvestigationLifecycleState.RUNNING.value, service_identity, current),
            )
            if updated.rowcount != 1:
                raise JobLeaseError("job lease is not owned by this service")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job_id, tenant_id),
            ).fetchone()
            return self._job_from_row(row)

    def requeue_job(
        self,
        job_id: str,
        tenant_id: str,
        service_identity: str,
        *,
        delay_seconds: int = 0,
        failure_code: str | None = None,
        failure_reason: str | None = None,
        reason: str = "retry scheduled",
        now: str | None = None,
    ) -> InvestigationJob:
        """Atomically return a lease-owned RUNNING job to the durable queue."""
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            LifecycleTransition,
        )

        if not job_id or not tenant_id or not service_identity:
            raise ValueError("job, tenant, and service identity are required")
        current = now or _now()
        available_at = (
            datetime.fromisoformat(current) + timedelta(seconds=max(0, int(delay_seconds)))
        ).isoformat()
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), str(tenant_id)),
            ).fetchone()
            if row is None:
                raise JobLeaseError("investigation job is unavailable")
            job = self._job_from_row(row)
            if (
                job.state.value != InvestigationLifecycleState.RUNNING.value
                or job.service_identity != service_identity
                or not job.lease_until
                or job.lease_until <= current
            ):
                raise JobLeaseError("job lease is not owned by this service")
            transition = LifecycleTransition.create(
                previous_state=job.state,
                next_state=InvestigationLifecycleState.QUEUED,
                tenant_id=job.tenant_id,
                case_id=job.case_id,
                investigation_id=job.investigation_id,
                execution_id=job.execution_id,
                job_id=job.job_id,
                actor_id=job.actor_id,
                service_identity=service_identity,
                correlation_id=job.correlation_id,
                reason=reason,
                attempt=job.attempts,
                iteration=job.iteration,
                recovery_authorized=True,
            )
            history = self._transition_history(job, transition)
            updated = connection.execute(
                """
                UPDATE investigation_jobs
                SET state=?, available_at=?, claimed_at=NULL, lease_until=NULL,
                    heartbeat_at=NULL, completed_at=NULL, failure_code=?,
                    failure_reason=?, state_history_json=?
                WHERE job_id=? AND tenant_id=? AND state=?
                  AND service_identity=? AND lease_until>?
                """,
                (
                    transition.next_state,
                    available_at,
                    _safe_error(failure_code) if failure_code else None,
                    _safe_error(failure_reason) if failure_reason else None,
                    _json(history), job.job_id, job.tenant_id,
                    InvestigationLifecycleState.RUNNING.value,
                    service_identity, current,
                ),
            )
            if updated.rowcount != 1:
                raise JobLeaseError("job lease was lost before requeue")
            self.record_transition(transition, connection=connection)
            refreshed = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            ).fetchone()
            return self._job_from_row(refreshed)

    def recover_expired_jobs(self, *, now: str | None = None, limit: int = 100) -> list[InvestigationJob]:
        from services.intelligence.runtime.investigation_lifecycle import (
            InvestigationLifecycleState,
            LifecycleTransition,
            TERMINAL_STATES,
        )

        current = now or _now()
        bounded_limit = max(1, min(int(limit), 500))
        recovered: list[InvestigationJob] = []
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM investigation_jobs
                WHERE state=? AND lease_until IS NOT NULL AND lease_until<=?
                ORDER BY lease_until, job_id LIMIT ?
                """,
                (InvestigationLifecycleState.RUNNING.value, current, bounded_limit),
            ).fetchall()
            for row in rows:
                job = self._job_from_row(row)
                if job.cancel_requested:
                    next_state = InvestigationLifecycleState.CANCELLED
                    reason = "cancellation honored during lease recovery"
                elif job.attempts < job.max_attempts:
                    next_state = InvestigationLifecycleState.QUEUED
                    reason = "expired worker lease recovered"
                else:
                    next_state = InvestigationLifecycleState.FAILED
                    reason = "worker lease expired after maximum attempts"
                transition = LifecycleTransition.create(
                    previous_state=job.state, next_state=next_state,
                    tenant_id=job.tenant_id, case_id=job.case_id,
                    investigation_id=job.investigation_id, execution_id=job.execution_id,
                    job_id=job.job_id, actor_id=job.actor_id, service_identity="lease-recovery",
                    correlation_id=job.correlation_id, reason=reason,
                    attempt=job.attempts, iteration=job.iteration,
                    recovery_authorized=next_state == InvestigationLifecycleState.QUEUED,
                )
                history = self._transition_history(job, transition)
                connection.execute(
                    """
                    UPDATE investigation_jobs
                    SET state=?, available_at=?, claimed_at=NULL, lease_until=NULL,
                        heartbeat_at=NULL, completed_at=?, failure_code=?,
                        failure_reason=?, state_history_json=?
                    WHERE job_id=? AND state=? AND lease_until<=?
                    """,
                    (
                        transition.next_state, current,
                        transition.timestamp if next_state in TERMINAL_STATES else None,
                        "lease_expired" if next_state == InvestigationLifecycleState.FAILED else None,
                        reason if next_state == InvestigationLifecycleState.FAILED else None,
                        _json(history), job.job_id, InvestigationLifecycleState.RUNNING.value, current,
                    ),
                )
                self.record_transition(transition, connection=connection)
                refreshed = connection.execute(
                    "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                    (job.job_id, job.tenant_id),
                ).fetchone()
                recovered.append(self._job_from_row(refreshed))
        return recovered

    def save_snapshot(
        self,
        snapshot: Any,
        *,
        job_id: str,
        execution_id: str,
        iteration: int,
        parent_snapshot_id: str | None = None,
        service_identity: str | None = None,
    ) -> Any:
        """Persist one immutable, tenant-scoped InvestigationSnapshot."""
        from services.intelligence.investigation.investigation_snapshot import InvestigationSnapshot

        if not isinstance(snapshot, InvestigationSnapshot):
            raise TypeError("snapshot must be an InvestigationSnapshot")
        snapshot.verify()
        if int(iteration) < 0:
            raise ValueError("snapshot iteration must be non-negative")
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            job_row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), snapshot.tenant_id),
            ).fetchone()
            if job_row is None or str(job_row["execution_id"]) != str(execution_id):
                raise PermissionError("snapshot job identity does not match tenant or execution")
            if str(job_row["case_id"]) != snapshot.case_id:
                raise PermissionError("snapshot case identity does not match job")
            if parent_snapshot_id:
                parent = connection.execute(
                    "SELECT tenant_id, case_id, investigation_id FROM investigation_snapshots WHERE snapshot_id=?",
                    (str(parent_snapshot_id),),
                ).fetchone()
                if parent is None or tuple(parent[key] for key in ("tenant_id", "case_id")) != (
                    snapshot.tenant_id, snapshot.case_id
                ):
                    raise PermissionError("snapshot parent lineage does not match investigation identity")
            same_snapshot = connection.execute(
                "SELECT * FROM investigation_snapshots WHERE snapshot_id=? AND tenant_id=?",
                (snapshot.snapshot_id, snapshot.tenant_id),
            ).fetchone()
            if same_snapshot is not None:
                if str(same_snapshot["job_id"]) != str(job_id) or str(same_snapshot["execution_id"]) != str(execution_id):
                    raise JobConflictError("snapshot ID is already bound to another durable execution")
                if same_snapshot["digest"] != snapshot.digest:
                    raise JobConflictError("snapshot ID conflicts with an immutable digest")
                connection.execute(
                    "UPDATE investigation_jobs SET snapshot_id=?, snapshot_digest=? WHERE job_id=? AND tenant_id=?",
                    (snapshot.snapshot_id, snapshot.digest, str(job_id), snapshot.tenant_id),
                )
                from services.intelligence.investigation.investigation_snapshot import InvestigationSnapshot as Snapshot
                return Snapshot.from_dict(json.loads(same_snapshot["snapshot_json"]))
            existing = connection.execute(
                "SELECT * FROM investigation_snapshots WHERE job_id=? AND iteration=?",
                (str(job_id), int(iteration)),
            ).fetchone()
            if existing is not None:
                if existing["digest"] != snapshot.digest:
                    raise JobConflictError("immutable snapshot iteration conflicts with existing digest")
                from services.intelligence.investigation.investigation_snapshot import InvestigationSnapshot as Snapshot
                return Snapshot.from_dict(json.loads(existing["snapshot_json"]))
            connection.execute(
                """INSERT INTO investigation_snapshots
                (snapshot_id, digest, job_id, execution_id, tenant_id, case_id,
                 investigation_id, actor_id, correlation_id, iteration, parent_snapshot_id,
                 snapshot_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.snapshot_id, snapshot.digest, str(job_id), str(execution_id), snapshot.tenant_id,
                    snapshot.case_id, str(job_row["investigation_id"]), snapshot.actor_id, snapshot.correlation_id,
                    int(iteration), parent_snapshot_id, _json(snapshot.to_dict()), _now(),
                ),
            )
            connection.execute(
                "UPDATE investigation_jobs SET snapshot_id=?, snapshot_digest=? WHERE job_id=? AND tenant_id=?",
                (snapshot.snapshot_id, snapshot.digest, str(job_id), snapshot.tenant_id),
            )
            self.record_audit_event(
                tenant_id=snapshot.tenant_id, job_id=str(job_id), event_type="INVESTIGATION_SNAPSHOT_PERSISTED",
                actor_id=snapshot.actor_id, service_identity=service_identity,
                correlation_id=snapshot.correlation_id, case_id=snapshot.case_id,
                investigation_id=str(job_row["investigation_id"]), execution_id=str(execution_id),
                metadata={"snapshot_id": snapshot.snapshot_id, "snapshot_digest": snapshot.digest,
                          "iteration": int(iteration), "parent_snapshot_id": parent_snapshot_id}, connection=connection,
            )
        return snapshot

    def get_snapshot(self, snapshot_id: str, tenant_id: str) -> Any | None:
        if not snapshot_id or not tenant_id:
            return None
        from services.intelligence.investigation.investigation_snapshot import InvestigationSnapshot
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM investigation_snapshots WHERE snapshot_id=? AND tenant_id=?",
                (str(snapshot_id), str(tenant_id)),
            ).fetchone()
        return InvestigationSnapshot.from_dict(json.loads(row["snapshot_json"])) if row else None

    def save_sufficiency_evaluation(
        self, result: Any, *, job_id: str, iteration: int, service_identity: str | None = None,
    ) -> Any:
        """Persist the safe contract projection exactly once per job iteration."""
        from services.intelligence.reasoning.evidence_sufficiency import EvidenceSufficiencyResult
        from services.intelligence.investigation.canonical import sha256_digest

        if not isinstance(result, EvidenceSufficiencyResult):
            raise TypeError("result must be an EvidenceSufficiencyResult")
        payload = result.to_dict()
        digest = sha256_digest({"job_id": str(job_id), "iteration": int(iteration), "result": payload})
        evaluation_id = f"SVE-{digest[:24]}"
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), result.tenant_id),
            ).fetchone()
            if row is None or str(row["case_id"]) != result.case_id or str(row["investigation_id"]) != result.investigation_id:
                raise PermissionError("sufficiency evaluation identity does not match job")
            existing = connection.execute(
                "SELECT * FROM investigation_sufficiency_evaluations WHERE job_id=? AND iteration=?",
                (str(job_id), int(iteration)),
            ).fetchone()
            if existing is not None:
                if existing["input_evidence_digest"] != result.input_evidence_digest:
                    raise JobConflictError("sufficiency evaluation iteration conflicts with existing digest")
                return result
            connection.execute(
                """INSERT INTO investigation_sufficiency_evaluations
                (evaluation_id, job_id, execution_id, tenant_id, case_id, investigation_id,
                 correlation_id, iteration, status, input_evidence_digest, result_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (evaluation_id, str(job_id), row["execution_id"], result.tenant_id, result.case_id,
                 result.investigation_id, result.correlation_id, int(iteration), result.status.value,
                 result.input_evidence_digest, _json(payload), _now()),
            )
            self.record_audit_event(
                tenant_id=result.tenant_id, job_id=str(job_id), event_type="EVIDENCE_SUFFICIENCY_EVALUATED",
                actor_id=row["actor_id"], service_identity=service_identity,
                correlation_id=result.correlation_id, case_id=result.case_id,
                investigation_id=result.investigation_id, execution_id=row["execution_id"],
                metadata={"evaluation_id": evaluation_id, "status": result.status.value,
                          "input_evidence_digest": result.input_evidence_digest, "iteration": int(iteration)},
                connection=connection,
            )
        return result

    def get_sufficiency_evaluation(self, job_id: str, tenant_id: str, iteration: int) -> Any | None:
        from services.intelligence.reasoning.evidence_sufficiency import EvidenceSufficiencyResult, SufficiencyStatus
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT result_json FROM investigation_sufficiency_evaluations WHERE job_id=? AND tenant_id=? AND iteration=?",
                (str(job_id), str(tenant_id), int(iteration)),
            ).fetchone()
        return EvidenceSufficiencyResult(**{
            **json.loads(row["result_json"]),
            "status": SufficiencyStatus(json.loads(row["result_json"])["status"]),
            "evidence_gaps": tuple(json.loads(row["result_json"]).get("evidence_gaps", [])),
            "supporting_evidence_ids": tuple(json.loads(row["result_json"]).get("supporting_evidence_ids", [])),
            "unresolved_hypotheses": tuple(json.loads(row["result_json"]).get("unresolved_hypotheses", [])),
        }) if row else None

    @staticmethod
    def _task_from_json(value: Mapping[str, Any]) -> Any:
        from datetime import datetime
        from services.intelligence.runtime.task import Task
        from services.intelligence.runtime.task_priority import TaskPriority
        def dt(key: str) -> Any:
            return datetime.fromisoformat(value[key]) if value.get(key) else None
        return Task(
            task_id=value["task_id"], execution_id=value["execution_id"], capability=value["capability"],
            payload=dict(value.get("payload") or {}), priority=TaskPriority(value.get("priority", "normal")),
            metadata=dict(value.get("metadata") or {}), attempt=int(value.get("attempt", 0)),
            parent_task_id=value.get("parent_task_id"), job_id=value.get("job_id"), tenant_id=value.get("tenant_id"),
            case_id=value.get("case_id"), investigation_id=value.get("investigation_id"),
            objective=value.get("objective"), required_evidence=list(value.get("required_evidence") or []),
            iteration=int(value.get("iteration", 0)), authorization_reference=value.get("authorization_reference"),
            budget_cost=float(value.get("budget_cost", 0.0)), created_at=dt("created_at"),
            available_at=dt("available_at"), deadline_at=dt("deadline_at"),
        )

    def create_follow_up_task(self, task: Any, *, job: InvestigationJob, service_identity: str | None = None) -> Any:
        from services.intelligence.runtime.investigation_runtime_policy import InvestigationRuntimePolicy
        policy = InvestigationRuntimePolicy()
        if not getattr(task, "task_id", None) or int(getattr(task, "iteration", -1)) != 1:
            raise ValueError("follow-up task lineage is invalid")
        if tuple(getattr(task, field, None) for field in ("job_id", "tenant_id", "case_id", "investigation_id")) != (
            job.job_id, job.tenant_id, job.case_id, job.investigation_id
        ):
            raise PermissionError("follow-up task identity does not match job")
        if not task.parent_task_id or not task.authorization_reference or task.capability not in policy.allowed_capabilities:
            raise PermissionError("follow-up task is not explicitly authorized")
        if policy._destructive(task.capability) or not task.required_evidence or not task.objective:
            raise PermissionError("follow-up task capability or objective is unsafe")
        if task.required_evidence[0] not in task.objective:
            raise PermissionError("follow-up objective is not derived from its evidence gap")
        safe_payload = {
            "case_id": job.case_id, "tenant_id": job.tenant_id, "investigation_id": job.investigation_id,
            "job_id": job.job_id, "correlation_id": job.correlation_id, "objective": task.objective,
            "required_evidence": list(task.required_evidence), "authorization_reference": task.authorization_reference,
            "iteration": 1,
        }
        if task.capability == "threat_intelligence_lookup":
            provider_request = (getattr(task, "payload", {}) or {}).get("provider_request")
            if not isinstance(provider_request, Mapping):
                raise PermissionError("provider follow-up request is missing")
            ioc_type = str(provider_request.get("ioc_type") or "").strip().lower()
            ioc_value = str(provider_request.get("ioc_value") or "").strip().lower()
            if ioc_type not in {"ip", "domain", "url", "hash", "email", "unknown"} or not ioc_value or len(ioc_value) > 2048:
                raise PermissionError("provider follow-up request is invalid")
            safe_payload["provider_request"] = {"ioc_type": ioc_type, "ioc_value": ioc_value}
        payload = {**task.to_dict(), "payload": safe_payload,
                   "metadata": {"provenance": "bounded_evidence_gap"}}
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (job.job_id, job.tenant_id),
            ).fetchone()
            if row is None:
                raise PermissionError("follow-up job is unavailable")
            if bool(row["cancel_requested"]):
                raise PermissionError("follow-up job is cancelled")
            existing = connection.execute(
                "SELECT * FROM investigation_follow_up_tasks WHERE job_id=? AND iteration=?",
                (job.job_id, 1),
            ).fetchone()
            if existing is not None:
                if existing["task_id"] != task.task_id or existing["idempotency_key"] != f"{job.job_id}:{task.task_id}":
                    raise JobConflictError("follow-up task conflicts with existing lineage")
                return self._task_from_json(json.loads(existing["task_json"]))
            connection.execute(
                """INSERT INTO investigation_follow_up_tasks
                (task_id, execution_id, parent_task_id, job_id, tenant_id, case_id, investigation_id,
                 capability, objective, required_evidence_json, authorization_reference, priority, iteration,
                 budget_cost, idempotency_key, task_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.task_id, job.execution_id, task.parent_task_id, job.job_id, job.tenant_id, job.case_id,
                 job.investigation_id, task.capability, task.objective, _json(task.required_evidence),
                 task.authorization_reference, task.priority.value, task.iteration, task.budget_cost,
                 f"{job.job_id}:{task.task_id}", _json(payload), _now()),
            )
            self.record_audit_event(
                tenant_id=job.tenant_id, job_id=job.job_id, event_type="FOLLOW_UP_TASK_CREATED",
                actor_id=job.actor_id, service_identity=service_identity, correlation_id=job.correlation_id,
                case_id=job.case_id, investigation_id=job.investigation_id, execution_id=job.execution_id,
                task_id=task.task_id, metadata={"parent_task_id": task.parent_task_id, "capability": task.capability,
                                                "iteration": 1, "budget_cost": task.budget_cost}, connection=connection,
            )
        return task

    def get_follow_up_task(self, job_id: str, tenant_id: str) -> Any | None:
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT task_json FROM investigation_follow_up_tasks WHERE job_id=? AND tenant_id=? AND iteration=1",
                (str(job_id), str(tenant_id)),
            ).fetchone()
        return self._task_from_json(json.loads(row["task_json"])) if row else None

    def schedule_follow_up(
        self, job_id: str, tenant_id: str, service_identity: str, *, now: str | None = None,
    ) -> InvestigationJob:
        """Atomically persist WAITING -> FOLLOW_UP -> QUEUED under the lease."""
        from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState, LifecycleTransition
        current = now or _now()
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?",
                (str(job_id), str(tenant_id)),
            ).fetchone()
            if row is None:
                raise JobLeaseError("follow-up job is unavailable")
            job = self._job_from_row(row)
            if (job.state != InvestigationLifecycleState.RUNNING or job.service_identity != service_identity
                    or not job.lease_until or job.lease_until <= current or job.cancel_requested):
                raise JobLeaseError("follow-up scheduling lease is not owned by this service")
            task_row = connection.execute(
                "SELECT task_id FROM investigation_follow_up_tasks WHERE job_id=? AND tenant_id=? AND iteration=1",
                (job.job_id, job.tenant_id),
            ).fetchone()
            if task_row is None:
                raise JobConflictError("follow-up task must be persisted before scheduling")
            transitions = []
            previous = job.state
            for target, reason in ((InvestigationLifecycleState.WAITING_FOR_EVIDENCE, "evidence insufficiency recorded"),
                                   (InvestigationLifecycleState.FOLLOW_UP, "authorized follow-up approved"),
                                   (InvestigationLifecycleState.QUEUED, "bounded follow-up requeued")):
                transitions.append(LifecycleTransition.create(
                    previous_state=previous, next_state=target, tenant_id=job.tenant_id, case_id=job.case_id,
                    investigation_id=job.investigation_id, execution_id=job.execution_id, job_id=job.job_id,
                    actor_id=job.actor_id, service_identity=service_identity, correlation_id=job.correlation_id,
                    reason=reason, attempt=job.attempts, iteration=1,
                    recovery_authorized=target == InvestigationLifecycleState.QUEUED,
                ))
                previous = target
            history = [*job.state_history, *[item.to_dict() for item in transitions]]
            connection.execute(
                """UPDATE investigation_jobs SET state=?, iteration=1, available_at=?, claimed_at=NULL,
                lease_until=NULL, heartbeat_at=NULL, completed_at=NULL, failure_code=NULL, failure_reason=NULL,
                state_history_json=? WHERE job_id=? AND tenant_id=? AND state=? AND service_identity=? AND lease_until>?""",
                (InvestigationLifecycleState.QUEUED.value, current, _json(history), job.job_id, job.tenant_id,
                 InvestigationLifecycleState.RUNNING.value, service_identity, current),
            )
            if connection.execute("SELECT changes() AS count").fetchone()["count"] != 1:
                raise JobLeaseError("follow-up scheduling lost its lease")
            for transition in transitions:
                self.record_transition(transition, connection=connection)
            self.record_audit_event(
                tenant_id=job.tenant_id, job_id=job.job_id, event_type="FOLLOW_UP_REQUEUED",
                actor_id=job.actor_id, service_identity=service_identity, correlation_id=job.correlation_id,
                case_id=job.case_id, investigation_id=job.investigation_id, execution_id=job.execution_id,
                task_id=task_row["task_id"], metadata={"iteration": 1}, connection=connection,
            )
            refreshed = connection.execute(
                "SELECT * FROM investigation_jobs WHERE job_id=? AND tenant_id=?", (job.job_id, job.tenant_id)
            ).fetchone()
            return self._job_from_row(refreshed)

    def reserve_provider_request(self, request: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        """Reserve one deterministic provider request; duplicates never re-invoke a provider."""
        required = ("request_id", "request_digest", "job_id", "execution_id", "task_id", "tenant_id",
                    "case_id", "investigation_id", "correlation_id", "capability", "iteration")
        if any(not str(request.get(key) or "").strip() for key in required):
            raise ValueError("provider request identity is incomplete")
        service_identity = str(request.get("service_identity") or "").strip()
        if not service_identity:
            raise PermissionError("provider request service identity is required")
        if int(request["iteration"]) != 1:
            raise ValueError("provider requests are limited to follow-up iteration one")
        payload = {
            "request_id": str(request["request_id"]), "request_digest": str(request["request_digest"]),
            "job_id": str(request["job_id"]), "execution_id": str(request["execution_id"]),
            "task_id": str(request["task_id"]), "tenant_id": str(request["tenant_id"]),
            "case_id": str(request["case_id"]), "investigation_id": str(request["investigation_id"]),
            "correlation_id": str(request["correlation_id"]), "capability": str(request["capability"]),
            "iteration": 1, "status": "IN_FLIGHT", "error_code": None,
            "observation_ids": [], "request": dict(request.get("request") or {}),
            "created_at": str(request.get("created_at") or _now()), "completed_at": None,
        }
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (payload["request_id"], payload["tenant_id"]),
            ).fetchone()
            if existing is not None:
                stored = self._provider_request_row(existing)
                if stored["request_digest"] != payload["request_digest"] or stored["job_id"] != payload["job_id"]:
                    raise JobConflictError("provider request identity conflicts with existing request")
                return stored, False
            job_row = connection.execute(
                "SELECT tenant_id, case_id, investigation_id, execution_id, actor_id, cancel_requested FROM investigation_jobs WHERE job_id=?",
                (payload["job_id"],),
            ).fetchone()
            if job_row is None or tuple(str(job_row[key]) for key in ("tenant_id", "case_id", "investigation_id", "execution_id")) != tuple(payload[key] for key in ("tenant_id", "case_id", "investigation_id", "execution_id")):
                raise PermissionError("provider request job identity does not match")
            if bool(job_row["cancel_requested"]):
                raise PermissionError("provider request job is cancelled")
            connection.execute(
                """INSERT INTO investigation_provider_requests
                (request_id, request_digest, job_id, execution_id, task_id, tenant_id, case_id,
                 investigation_id, correlation_id, capability, iteration, status, error_code,
                 observation_ids_json, request_json, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (payload["request_id"], payload["request_digest"], payload["job_id"], payload["execution_id"],
                 payload["task_id"], payload["tenant_id"], payload["case_id"], payload["investigation_id"],
                 payload["correlation_id"], payload["capability"], 1, "IN_FLIGHT", None, "[]",
                 _json(payload["request"]), payload["created_at"], None),
            )
            self.record_audit_event(
                tenant_id=payload["tenant_id"], job_id=payload["job_id"], event_type="PROVIDER_REQUEST_RESERVED",
                actor_id=job_row["actor_id"], service_identity=service_identity,
                correlation_id=payload["correlation_id"], case_id=payload["case_id"],
                investigation_id=payload["investigation_id"], execution_id=payload["execution_id"],
                task_id=payload["task_id"], metadata={"request_id": payload["request_id"],
                                                       "request_digest": payload["request_digest"],
                                                       "capability": payload["capability"]}, connection=connection,
            )
        return payload, True

    @staticmethod
    def _provider_request_row(row: Any) -> dict[str, Any]:
        return {
            "request_id": row["request_id"], "request_digest": row["request_digest"], "job_id": row["job_id"],
            "execution_id": row["execution_id"], "task_id": row["task_id"], "tenant_id": row["tenant_id"],
            "case_id": row["case_id"], "investigation_id": row["investigation_id"],
            "correlation_id": row["correlation_id"], "capability": row["capability"],
            "iteration": int(row["iteration"]), "status": row["status"], "error_code": row["error_code"],
            "observation_ids": json.loads(row["observation_ids_json"] or "[]"),
            "request": json.loads(row["request_json"] or "{}"), "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }

    def get_provider_request(self, request_id: str, tenant_id: str) -> dict[str, Any] | None:
        if not request_id or not tenant_id:
            return None
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
        return self._provider_request_row(row) if row else None

    def complete_provider_request(
        self, request_id: str, tenant_id: str, *, status: str, observation_ids: list[str] | tuple[str, ...] = (),
        error_code: str | None = None, service_identity: str,
    ) -> dict[str, Any]:
        allowed = {"COMPLETED", "FAILED", "REPLAYABLE"}
        if str(status).upper() not in allowed:
            raise ValueError("provider request status is invalid")
        if not str(service_identity or "").strip():
            raise PermissionError("provider request service identity is required")
        observations = sorted(set(str(item) for item in observation_ids if str(item)))
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
            if row is None:
                raise JobConflictError("provider request is unavailable")
            updated = connection.execute(
                """UPDATE investigation_provider_requests SET status=?, error_code=?,
                observation_ids_json=?, completed_at=? WHERE request_id=? AND tenant_id=? AND status=?""",
                (str(status).upper(), _safe_error(error_code) if error_code else None, _json(observations), _now(),
                 str(request_id), str(tenant_id), "IN_FLIGHT"),
            )
            if updated.rowcount != 1 and row["status"] != str(status).upper():
                raise JobConflictError("provider request completion raced another worker")
            refreshed = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
            stored = self._provider_request_row(refreshed)
            self.record_audit_event(
                tenant_id=stored["tenant_id"], job_id=stored["job_id"], event_type="PROVIDER_REQUEST_COMPLETED",
                service_identity=service_identity, correlation_id=stored["correlation_id"], case_id=stored["case_id"],
                investigation_id=stored["investigation_id"], execution_id=stored["execution_id"], task_id=stored["task_id"],
                metadata={"request_id": stored["request_id"], "status": stored["status"],
                          "observation_count": len(stored["observation_ids"]), "error_code": stored["error_code"]},
                connection=connection,
            )
            return stored

    def reserve_provider_budget(
        self,
        *,
        request_id: str,
        tenant_id: str,
        job_id: str,
        investigation_id: str,
        execution_id: str,
        task_id: str,
        iteration: int,
        request_digest: str,
        provider_names: list[str] | tuple[str, ...],
        cost_per_provider: float = 1.0,
        tenant_quota: float = 1.0,
        now: str | None = None,
        service_identity: str,
    ) -> dict[str, Any]:
        """Atomically reserve tenant quota exactly once for a provider request."""
        providers = tuple(sorted(set(str(item).strip() for item in provider_names if str(item).strip())))
        if not all((request_id, tenant_id, job_id, investigation_id, execution_id, task_id, request_digest, service_identity)):
            raise ProviderBudgetError("provider budget identity is incomplete")
        if int(iteration) != 1 or not providers or float(cost_per_provider) <= 0 or float(tenant_quota) < 0:
            raise ProviderBudgetError("provider budget parameters are invalid")
        reserved_at = str(now or _now())
        total_cost = float(len(providers)) * float(cost_per_provider)
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
            if request is None:
                raise ProviderBudgetError("provider request is unavailable")
            if any(str(request[key]) != str(value) for key, value in {
                "job_id": job_id, "investigation_id": investigation_id, "execution_id": execution_id,
                "task_id": task_id, "request_digest": request_digest,
            }.items()):
                raise ProviderBudgetError("provider budget request identity does not match")
            existing_rows = connection.execute(
                "SELECT * FROM investigation_provider_budget_ledger WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchall()
            if existing_rows:
                existing_providers = tuple(sorted(str(row["provider_name"]) for row in existing_rows))
                if existing_providers != providers:
                    raise ProviderBudgetError("provider budget reservation conflicts with existing request")
                return {
                    "request_id": str(request_id), "tenant_id": str(tenant_id),
                    "provider_names": list(existing_providers),
                    "reserved_cost": sum(float(row["reserved_cost"]) for row in existing_rows),
                    "consumed_cost": sum(float(row["consumed_cost"]) for row in existing_rows),
                    "created": False,
                }
            usage_row = connection.execute(
                "SELECT COALESCE(SUM(consumed_cost), 0) AS consumed FROM investigation_provider_budget_ledger WHERE tenant_id=?",
                (str(tenant_id),),
            ).fetchone()
            consumed = float(usage_row["consumed"] or 0.0)
            if consumed + total_cost > float(tenant_quota):
                raise ProviderBudgetError("tenant provider quota exhausted")
            for provider_name in providers:
                connection.execute(
                    """
                    INSERT INTO investigation_provider_budget_ledger
                    (ledger_id, request_id, tenant_id, job_id, investigation_id, execution_id,
                     task_id, iteration, provider_name, request_digest, reserved_cost,
                     consumed_cost, status, outcome, reserved_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PBL-{sha256_digest({'request_id': request_id, 'provider': provider_name})[:24]}",
                        str(request_id), str(tenant_id), str(job_id), str(investigation_id), str(execution_id),
                        str(task_id), int(iteration), provider_name, str(request_digest),
                        float(cost_per_provider), float(cost_per_provider), "RESERVED", None, reserved_at, None,
                    ),
                )
            self.record_audit_event(
                tenant_id=str(tenant_id), job_id=str(job_id), event_type="PROVIDER_QUOTA_RESERVED",
                service_identity=str(service_identity), correlation_id=request["correlation_id"],
                case_id=request["case_id"], investigation_id=str(investigation_id), execution_id=str(execution_id),
                task_id=str(task_id), metadata={
                    "request_id": str(request_id), "request_digest": str(request_digest),
                    "provider_names": list(providers), "reserved_cost": total_cost,
                    "tenant_quota": float(tenant_quota), "prior_consumed_cost": consumed,
                }, connection=connection,
            )
        return {
            "request_id": str(request_id), "tenant_id": str(tenant_id),
            "provider_names": list(providers), "reserved_cost": total_cost,
            "consumed_cost": total_cost, "created": True,
        }

    def finalize_provider_budget(
        self,
        *,
        request_id: str,
        tenant_id: str,
        status: str,
        outcome: str,
        service_identity: str,
    ) -> list[dict[str, Any]]:
        allowed = {"CONSUMED", "FAILED", "REPLAYED"}
        normalized = str(status).upper()
        if normalized not in allowed:
            raise ProviderBudgetError("provider budget outcome is invalid")
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM investigation_provider_budget_ledger WHERE request_id=? AND tenant_id=? ORDER BY provider_name",
                (str(request_id), str(tenant_id)),
            ).fetchall()
            if not rows:
                raise ProviderBudgetError("provider budget reservation is unavailable")
            request = connection.execute(
                "SELECT case_id, correlation_id FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
            connection.execute(
                "UPDATE investigation_provider_budget_ledger SET status=?, outcome=?, completed_at=? WHERE request_id=? AND tenant_id=? AND status=?",
                (normalized, str(outcome)[:128], _now(), str(request_id), str(tenant_id), "RESERVED"),
            )
            refreshed = connection.execute(
                "SELECT * FROM investigation_provider_budget_ledger WHERE request_id=? AND tenant_id=? ORDER BY provider_name",
                (str(request_id), str(tenant_id)),
            ).fetchall()
            first = refreshed[0]
            self.record_audit_event(
                tenant_id=str(tenant_id), job_id=first["job_id"], event_type="PROVIDER_QUOTA_FINALIZED",
                service_identity=service_identity, correlation_id=request["correlation_id"],
                case_id=request["case_id"],
                investigation_id=first["investigation_id"], execution_id=first["execution_id"],
                task_id=first["task_id"], metadata={
                    "request_id": str(request_id), "status": normalized,
                    "outcome": str(outcome)[:128],
                    "consumed_cost": sum(float(row["consumed_cost"]) for row in refreshed),
                }, connection=connection,
            )
        return [dict(row) for row in refreshed]

    def provider_budget_for_tenant(self, tenant_id: str) -> dict[str, float]:
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(consumed_cost), 0) AS consumed, COALESCE(SUM(reserved_cost), 0) AS reserved FROM investigation_provider_budget_ledger WHERE tenant_id=?",
                (str(tenant_id),),
            ).fetchone()
        return {"tenant_id": str(tenant_id), "consumed_cost": float(row["consumed"] or 0.0), "reserved_cost": float(row["reserved"] or 0.0)}

    def link_provider_observations(
        self,
        *,
        request_id: str,
        tenant_id: str,
        observation_ids: list[str] | tuple[str, ...],
        authorization_reference: str,
        capability: str,
        service_identity: str,
    ) -> list[dict[str, Any]]:
        references = tuple(sorted(set(str(item) for item in observation_ids if str(item))))
        if not references or not authorization_reference or not capability or not service_identity:
            raise ProviderObservationLineageError("provider observation lineage is incomplete")
        with self.db.session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT * FROM investigation_provider_requests WHERE request_id=? AND tenant_id=?",
                (str(request_id), str(tenant_id)),
            ).fetchone()
            if request is None:
                raise ProviderObservationLineageError("provider request lineage is unavailable")
            linked: list[dict[str, Any]] = []
            for observation_id in references:
                existing = connection.execute(
                    "SELECT * FROM investigation_provider_observation_links WHERE observation_id=? AND request_id=?",
                    (observation_id, str(request_id)),
                ).fetchone()
                if existing is not None:
                    if any(str(existing[key]) != str(value) for key, value in {
                        "request_id": request_id, "tenant_id": tenant_id,
                        "job_id": request["job_id"], "investigation_id": request["investigation_id"],
                        "execution_id": request["execution_id"], "task_id": request["task_id"],
                        "request_digest": request["request_digest"],
                    }.items()):
                        raise ProviderObservationLineageError("provider observation lineage conflicts")
                    linked.append(dict(existing))
                    continue
                payload = {
                    "observation_id": observation_id, "request_id": request_id,
                    "request_digest": request["request_digest"], "tenant_id": tenant_id,
                    "job_id": request["job_id"], "investigation_id": request["investigation_id"],
                    "execution_id": request["execution_id"], "task_id": request["task_id"],
                    "iteration": int(request["iteration"]), "capability": capability,
                    "authorization_reference": authorization_reference,
                    "correlation_id": request["correlation_id"], "linked_at": _now(),
                }
                connection.execute(
                    """INSERT INTO investigation_provider_observation_links
                    (observation_id, request_id, request_digest, tenant_id, job_id, investigation_id,
                     execution_id, task_id, iteration, capability, authorization_reference,
                     correlation_id, linked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuple(payload.values()),
                )
                linked.append(payload)
                self.record_audit_event(
                    tenant_id=tenant_id, job_id=request["job_id"], event_type="PROVIDER_OBSERVATION_LINKED",
                    service_identity=str(service_identity), correlation_id=request["correlation_id"],
                    case_id=request["case_id"], investigation_id=request["investigation_id"],
                    execution_id=request["execution_id"], task_id=request["task_id"],
                    metadata={"request_id": request_id, "observation_id": observation_id,
                              "request_digest": request["request_digest"]}, connection=connection,
                )
        return linked

    def verify_provider_observation_links(
        self,
        *,
        request_id: str,
        tenant_id: str,
        job_id: str,
        investigation_id: str,
        execution_id: str,
        task_id: str,
        observation_ids: list[str] | tuple[str, ...],
    ) -> list[dict[str, Any]]:
        references = tuple(sorted(set(str(item) for item in observation_ids if str(item))))
        with self.db.session() as connection:
            rows = []
            for observation_id in references:
                row = connection.execute(
                    "SELECT * FROM investigation_provider_observation_links WHERE observation_id=? AND request_id=?",
                    (observation_id, str(request_id)),
                ).fetchone()
                if row is None or any(str(row[key]) != str(value) for key, value in {
                    "request_id": request_id, "tenant_id": tenant_id, "job_id": job_id,
                    "investigation_id": investigation_id, "execution_id": execution_id, "task_id": task_id,
                }.items()):
                    raise ProviderObservationLineageError("provider observation lineage is invalid")
                rows.append(dict(row))
        return rows

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

    def save_provider_health(
        self,
        *,
        execution_id: str,
        tenant_id: str,
        snapshots: list[Mapping[str, Any]],
        request_id: str | None = None,
        job_id: str | None = None,
        task_id: str | None = None,
        investigation_id: str | None = None,
        iteration: int | None = None,
        correlation_id: str | None = None,
        outcome: str | None = None,
    ) -> None:
        with self.db.session() as connection:
            for item in snapshots:
                provider = str(item.get("provider") or item.get("provider_name") or "unknown")[:128]
                connection.execute(
                    """
                    INSERT INTO investigation_provider_health_snapshots
                    (snapshot_id, execution_id, tenant_id, provider_name, health_status,
                     checked_at, latency_ms, failure_count, availability_state,
                     policy_decision, unavailable_reason, request_id, job_id, task_id,
                     investigation_id, iteration, correlation_id, outcome)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PHS-{uuid4()}", execution_id, tenant_id, provider,
                        str(item.get("status") or "UNAVAILABLE"),
                        str(item.get("timestamp") or item.get("checked_at") or _now()),
                        item.get("latency_ms"), int(item.get("failure_count") or 0),
                        str(item.get("status") or "UNAVAILABLE"),
                        str(item.get("policy_decision") or "allowed"),
                        _safe_error(item.get("unavailable_reason")) if item.get("unavailable_reason") else None,
                        request_id, job_id, task_id, investigation_id, iteration, correlation_id,
                        _safe_error(outcome) if outcome else None,
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
                       unavailable_reason, request_id, job_id, task_id,
                       investigation_id, iteration, correlation_id, outcome
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
    "JobConflictError",
    "JobLeaseError",
    "ProviderBudgetError",
    "ProviderObservationLineageError",
]
