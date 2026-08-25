"""Controlled persistence for tenant-bound normalized provider observations."""

from __future__ import annotations

import json
import sqlite3
import base64
import hashlib
import hmac
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Iterable

from database.connection import database
from .errors import (
    ProviderObservationCursorExpiredError,
    ProviderObservationCursorOrderingMismatchError,
    ProviderObservationCursorScopeMismatchError,
    ProviderObservationInvalidCursorSignatureError,
    ProviderObservationInvalidPageSizeError,
    ProviderObservationMalformedCursorError,
    ProviderObservationProjectionBoundedError,
    ProviderObservationUnsupportedCursorVersionError,
    RepositoryError,
)
from config.runtime import RuntimeConfig
from services.intelligence.investigation.provider_observation import (
    ProviderObservation,
    ProviderObservationIntegrityError,
)
from services.intelligence.investigation.provider_observation_lifecycle import (
    ProviderObservationLifecycleError,
    ProviderObservationLifecycleEvent,
    ProviderObservationLifecycleRecord,
    ProviderObservationLifecycleStatus,
    ProviderObservationRetentionPolicy,
    utc_now,
)
from services.observability import ObservabilityService


class ProviderObservationRepository:
    """Persist only normalized observation contracts, never raw provider payloads."""

    PROJECTION_ORDERING = "observation_id:asc"
    DEFAULT_PAGE_SIZE = 100
    CURSOR_VERSION = 1
    CURSOR_TTL_SECONDS = 900

    def __init__(
        self,
        db=None,
        *,
        retention_policy=None,
        clock=None,
        authorization=None,
        max_projection_observations=None,
        max_projection_events=None,
        replay_batch_size=None,
        observer=None,
    ):
        self.db = db or database
        self.retention_policy = retention_policy or ProviderObservationRetentionPolicy()
        if not isinstance(self.retention_policy, ProviderObservationRetentionPolicy):
            raise ValueError("provider observation retention policy is invalid")
        self.clock = clock or utc_now
        self.authorization = authorization
        self.observer = observer or ObservabilityService()
        configured = RuntimeConfig.from_environment()
        self.max_projection_observations = self._positive_bound(
            max_projection_observations
            if max_projection_observations is not None
            else getattr(configured, "provider_observation_projection_max", 1000),
            "provider observation projection maximum",
        )
        self.max_projection_events = self._positive_bound(
            max_projection_events
            if max_projection_events is not None
            else getattr(configured, "provider_observation_lifecycle_event_projection_max", 1000),
            "provider observation lifecycle-event projection maximum",
        )
        self.replay_batch_size = replay_batch_size if replay_batch_size is not None else getattr(configured, "provider_observation_replay_batch_size", 100)
        if isinstance(self.replay_batch_size, bool) or not isinstance(self.replay_batch_size, int) or not 0 < self.replay_batch_size <= 1000:
            raise ValueError("provider observation replay batch size is invalid")
        self._ensure_schema()

    @staticmethod
    def _positive_bound(value: Any, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{label} must be a positive integer")
        return value

    @dataclass(frozen=True)
    class AnalystProjectionPage:
        records: tuple[tuple[ProviderObservation, ProviderObservationLifecycleRecord, tuple[ProviderObservationLifecycleEvent, ...]], ...]
        page_size: int
        has_more: bool
        next_cursor: str | None
        ordering: str = "observation_id:asc"

        @property
        def complete(self) -> bool:
            return not self.has_more

    def _cursor_key(self) -> bytes:
        return RuntimeConfig.from_environment().secret_key.encode("utf-8")

    @staticmethod
    def _encode_cursor_payload(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode_cursor_payload(value: str) -> dict[str, Any]:
        try:
            padded = value + ("=" * (-len(value) % 4))
            decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
            payload = json.loads(decoded.decode("utf-8"))
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError, base64.binascii.Error) as exc:
            raise ProviderObservationMalformedCursorError("provider observation cursor is malformed") from exc
        if not isinstance(payload, dict):
            raise ProviderObservationMalformedCursorError("provider observation cursor is malformed")
        return payload

    def _encode_cursor(self, *, tenant_id: str, case_id: str, actor_id: str, correlation_id: str, page_size: int, last_observation_id: str) -> str:
        now = int(time.time())
        payload = {
            "version": self.CURSOR_VERSION,
            "tenant_id": tenant_id,
            "case_id": case_id,
            "actor_id": actor_id,
            "correlation_id": correlation_id,
            "ordering": self.PROJECTION_ORDERING,
            "page_size": page_size,
            "last_observation_id": last_observation_id,
            "issued_at": now,
            "expires_at": now + self.CURSOR_TTL_SECONDS,
        }
        encoded = self._encode_cursor_payload(payload)
        signature = hmac.new(self._cursor_key(), encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}"

    def _decode_cursor(self, cursor: str, *, tenant_id: str, case_id: str, actor_id: str, correlation_id: str, page_size: int | None) -> tuple[str, int]:
        if not isinstance(cursor, str) or not cursor or cursor.count(".") != 1:
            raise ProviderObservationMalformedCursorError("provider observation cursor is malformed")
        encoded, supplied_signature = cursor.split(".", 1)
        try:
            supplied = base64.urlsafe_b64decode(supplied_signature + ("=" * (-len(supplied_signature) % 4)))
        except (ValueError, TypeError, base64.binascii.Error) as exc:
            raise ProviderObservationMalformedCursorError("provider observation cursor is malformed") from exc
        expected = hmac.new(self._cursor_key(), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            raise ProviderObservationInvalidCursorSignatureError("provider observation cursor signature is invalid")
        payload = self._decode_cursor_payload(encoded)
        if payload.get("version") != self.CURSOR_VERSION:
            raise ProviderObservationUnsupportedCursorVersionError("provider observation cursor version is unsupported")
        if payload.get("ordering") != self.PROJECTION_ORDERING:
            raise ProviderObservationCursorOrderingMismatchError("provider observation cursor ordering is invalid")
        if page_size is not None and payload.get("page_size") != page_size:
            raise ProviderObservationInvalidPageSizeError("provider observation cursor page size is invalid")
        if not isinstance(payload.get("page_size"), int) or isinstance(payload["page_size"], bool):
            raise ProviderObservationInvalidPageSizeError("provider observation cursor page size is invalid")
        if not isinstance(payload.get("last_observation_id"), str) or not payload["last_observation_id"]:
            raise ProviderObservationMalformedCursorError("provider observation cursor is malformed")
        if not isinstance(payload.get("expires_at"), int) or int(time.time()) >= payload["expires_at"]:
            raise ProviderObservationCursorExpiredError("provider observation cursor has expired")
        expected_scope = {
            "tenant_id": tenant_id,
            "case_id": case_id,
            "actor_id": actor_id,
            "correlation_id": correlation_id,
        }
        if any(payload.get(key) != value for key, value in expected_scope.items()):
            raise ProviderObservationCursorScopeMismatchError("provider observation cursor scope does not match request")
        return payload["last_observation_id"], payload["page_size"]

    def _validate_page_size(self, page_size: Any) -> int:
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0 or page_size > self.max_projection_observations:
            raise ProviderObservationInvalidPageSizeError("provider observation page size is invalid")
        return page_size

    def _replay_observability(self, event: str, *, started: float, tenant_id: Any, correlation_id: Any, observation_count: int, batch_count: int, result: str) -> None:
        try:
            self.observer.event(
                event,
                tenant_id=str(tenant_id or "unknown"),
                correlation_id=str(correlation_id or "unknown"),
                observation_count=observation_count,
                batch_count=batch_count,
                batch_size=self.replay_batch_size,
                result=result,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception:
            return None

    def _replay_failure_event(self, exc: Exception) -> str:
        if isinstance(exc, PermissionError):
            return "replay_authorization_rejection"
        message = str(exc).lower()
        if "reference is malformed" in message:
            return "replay_malformed_reference"
        if "references are duplicated" in message:
            return "replay_duplicate_reference"
        if "required provider observation is unavailable" in message:
            return "replay_missing_observation"
        if "invalidated" in message or "expired" in message or "lifecycle" in message:
            return "replay_lifecycle_rejection"
        if "integrity" in message or "provenance" in message:
            return "replay_integrity_failure"
        return "replay_rejection"

    def _emit_observability(self, event: str, **fields: Any) -> None:
        try:
            self.observer.event(event, **fields)
        except Exception:
            return None

    @staticmethod
    def _projection_error_category(exc: Exception) -> str:
        if isinstance(exc, ProviderObservationInvalidCursorSignatureError):
            return "invalid_cursor_signature"
        if isinstance(exc, ProviderObservationCursorExpiredError):
            return "cursor_expired"
        if isinstance(exc, ProviderObservationUnsupportedCursorVersionError):
            return "unsupported_cursor_version"
        if isinstance(exc, ProviderObservationCursorScopeMismatchError):
            return "cursor_scope_mismatch"
        if isinstance(exc, ProviderObservationCursorOrderingMismatchError):
            return "ordering_mismatch"
        if isinstance(exc, ProviderObservationInvalidPageSizeError):
            return "invalid_page_size"
        if isinstance(exc, ProviderObservationMalformedCursorError):
            return "invalid_cursor"
        message = str(exc).lower()
        if "lifecycle-event bound" in message:
            return "lifecycle_event_bound_exceeded"
        if isinstance(exc, ProviderObservationProjectionBoundedError):
            return "projection_bound_exceeded"
        if "signature" in message:
            return "invalid_cursor_signature"
        if "expired" in message:
            return "cursor_expired"
        if "scope" in message:
            return "cursor_scope_mismatch"
        if "ordering" in message:
            return "ordering_mismatch"
        if "page size" in message:
            return "invalid_page_size"
        if "cursor" in message:
            return "invalid_cursor"
        return "projection_failure"

    def _emit_projection_telemetry(
        self,
        event: str,
        *,
        started: float,
        tenant_id: Any,
        correlation_id: Any,
        paginated: bool,
        page_phase: str,
        final_page: bool,
        page_size: int | None,
        observation_count: int,
        lifecycle_event_count: int,
        has_more: bool,
        observation_select_count: int,
        lifecycle_event_select_count: int,
        result: str,
        error_category: str | None = None,
    ) -> None:
        self._emit_observability(
            event,
            tenant_id=str(tenant_id or "unknown"),
            correlation_id=str(correlation_id or "unknown"),
            paginated=paginated,
            page_phase=page_phase,
            final_page=final_page,
            page_size=page_size,
            observation_count=observation_count,
            lifecycle_event_count=lifecycle_event_count,
            has_more=has_more,
            observation_select_count=observation_select_count,
            lifecycle_event_select_count=lifecycle_event_select_count,
            query_count=observation_select_count + lifecycle_event_select_count,
            result=result,
            error_category=error_category,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def _emit_lifecycle_telemetry(
        self,
        event: str,
        *,
        started: float,
        tenant_id: Any,
        correlation_id: Any,
        state: dict[str, Any],
        result: str,
        error_category: str | None = None,
    ) -> None:
        self._emit_observability(
            event,
            tenant_id=str(tenant_id or "unknown"),
            correlation_id=str(correlation_id or "unknown"),
            operation="provider_observation_lifecycle_transition",
            previous_status=state.get("previous_status"),
            resulting_status=state.get("resulting_status"),
            target_status=state.get("target_status"),
            phase=state.get("phase"),
            result=result,
            error_category=error_category,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    @contextmanager
    def _observe_lifecycle_transition(
        self,
        *,
        started: float,
        tenant_id: str,
        correlation_id: str,
        state: dict[str, Any],
    ):
        try:
            yield
        except Exception as exc:
            if self._is_sqlite_lifecycle_lock(exc):
                event = "provider_observation_lifecycle_lock_conflict"
                category = "sqlite_lock_conflict"
            elif isinstance(exc, ProviderObservationLifecycleError) and "invalid provider observation lifecycle transition" in str(exc):
                event = "provider_observation_lifecycle_invalid_transition"
                category = "invalid_transition"
            elif isinstance(exc, ProviderObservationLifecycleError) and "lifecycle conflict" in str(exc):
                event = "provider_observation_lifecycle_conflict"
                category = "compare_and_set_conflict"
            elif state.get("phase") == "audit_insertion":
                event = "provider_observation_lifecycle_audit_insertion_failure"
                category = "audit_insertion_failure"
            else:
                event = "provider_observation_lifecycle_failure"
                category = "unexpected_database_failure" if isinstance(exc, sqlite3.Error) else "transition_failure"
            self._emit_lifecycle_telemetry(
                event,
                started=started,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                state=state,
                result="failure",
                error_category=category,
            )
            raise
        self._emit_lifecycle_telemetry(
            "provider_observation_lifecycle_success",
            started=started,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            state=state,
            result="success",
        )

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_observations (
                    observation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    correlation_id TEXT,
                    actor_id TEXT,
                    provider_name TEXT NOT NULL,
                    provider_version TEXT,
                    observation_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    normalized_observation_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    evidence_references_json TEXT NOT NULL,
                    integrity_digest TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    invalidated INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_observations_tenant_case "
                "ON provider_observations(tenant_id, case_id, observation_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_observations_correlation "
                "ON provider_observations(tenant_id, correlation_id)"
            )
            for column, definition in (
                ("lifecycle_status", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
                ("lifecycle_updated_at", "TEXT"),
                ("lifecycle_stale_at", "TEXT"),
                ("lifecycle_expires_at", "TEXT"),
                ("lifecycle_invalidated_at", "TEXT"),
                ("lifecycle_invalidated_by", "TEXT"),
                ("lifecycle_invalidation_reason", "TEXT"),
            ):
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        "PRAGMA table_info(provider_observations)"
                    ).fetchall()
                }
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE provider_observations ADD COLUMN {column} {definition}"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_observations_lifecycle "
                "ON provider_observations(tenant_id, lifecycle_status, lifecycle_expires_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_observation_lifecycle_events (
                    audit_event_id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    previous_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    event_timestamp TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    event_digest TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_observation_lifecycle_events_scope "
                "ON provider_observation_lifecycle_events(tenant_id, case_id, observation_id, event_timestamp)"
            )

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ProviderObservationLifecycleError("lifecycle clock must return timezone-aware datetime")
        return value.isoformat()

    def _reference_time(self, as_of: datetime | None = None) -> datetime:
        value = as_of if as_of is not None else self.clock()
        self._timestamp(value)
        return value

    def _lifecycle_fields(self, observation: ProviderObservation, as_of: datetime) -> dict[str, Any]:
        stale_at = self.retention_policy.stale_at(observation)
        expires_at = self.retention_policy.expires_at(observation)
        status = self.retention_policy.classify(observation, as_of).value
        return {
            "status": status,
            "updated_at": self._timestamp(as_of),
            "stale_at": stale_at.isoformat() if stale_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    @staticmethod
    def _row_lifecycle(row: Any, observation: ProviderObservation) -> ProviderObservationLifecycleRecord:
        updated_at = row["lifecycle_updated_at"] or observation.observed_at
        try:
            return ProviderObservationLifecycleRecord(
                observation_id=observation.observation_id,
                tenant_id=observation.tenant_id,
                case_id=observation.case_id,
                correlation_id=observation.correlation_id,
                actor_id=observation.actor_id,
                provider_name=observation.provider_name,
                status=str(row["lifecycle_status"] or ProviderObservationLifecycleStatus.ACTIVE.value),
                observed_at=observation.observed_at,
                stale_at=row["lifecycle_stale_at"],
                expires_at=row["lifecycle_expires_at"],
                invalidated_at=row["lifecycle_invalidated_at"],
                invalidated_by=row["lifecycle_invalidated_by"],
                invalidation_reason=row["lifecycle_invalidation_reason"],
                updated_at=updated_at,
            )
        except (KeyError, TypeError, ValueError, ProviderObservationLifecycleError) as exc:
            raise RepositoryError("stored provider observation lifecycle is invalid") from exc

    def _row_for_scope(
        self,
        connection: Any,
        observation_id: str,
        tenant_id: str,
        case_id: str,
        correlation_id: str | None = None,
    ) -> Any:
        return connection.execute(
            """
            SELECT * FROM provider_observations
            WHERE observation_id=? AND tenant_id=? AND case_id=?
              AND (? IS NULL OR correlation_id=?)
            """,
            (str(observation_id), tenant_id, case_id, correlation_id, correlation_id),
        ).fetchone()

    def _authorize_lifecycle(
        self,
        *,
        authorization_context: Any,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        permission: str,
    ) -> None:
        if self.authorization is None or not callable(getattr(self.authorization, "require_permission", None)):
            raise PermissionError("provider observation lifecycle authorization is unavailable")
        if not authorization_context:
            raise PermissionError("provider observation lifecycle authorization is required")
        context_tenant = str(getattr(authorization_context, "tenant_id", "") or "")
        context_actor = str(getattr(authorization_context, "actor_id", "") or "")
        if context_tenant != str(tenant_id):
            raise PermissionError("provider observation lifecycle tenant mismatch")
        if context_actor != str(actor_id):
            raise PermissionError("provider observation lifecycle actor mismatch")
        context_correlation = getattr(authorization_context, "correlation_id", None)
        if context_correlation is not None and str(context_correlation) != str(correlation_id):
            raise PermissionError("provider observation lifecycle correlation mismatch")
        try:
            self.authorization.require_permission(authorization_context, tenant_id, permission)
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("provider observation lifecycle authorization denied") from exc

    @staticmethod
    def _is_sqlite_lifecycle_lock(exc: BaseException) -> bool:
        seen: set[int] = set()
        current: BaseException | None = exc
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, sqlite3.OperationalError):
                message = str(current).lower()
                return any(
                    marker in message
                    for marker in (
                        "database is locked",
                        "database table is locked",
                        "database schema is locked",
                        "database is busy",
                    )
                )
            current = current.__cause__ or current.__context__
        return False

    @contextmanager
    def _lifecycle_session(self):
        try:
            with self.db.session() as connection:
                yield connection
        except Exception as exc:
            if self._is_sqlite_lifecycle_lock(exc):
                raise ProviderObservationLifecycleError(
                    "provider observation lifecycle conflict"
                ) from exc
            raise

    @staticmethod
    def _load_observation(row: Any) -> ProviderObservation:
        try:
            return ProviderObservation.from_dict(ProviderObservationRepository._row_payload(row))
        except (KeyError, TypeError, ValueError, ProviderObservationIntegrityError) as exc:
            raise RepositoryError("stored provider observation failed integrity validation") from exc

    def _effective_status(
        self,
        row: Any,
        observation: ProviderObservation,
        as_of: datetime,
    ) -> ProviderObservationLifecycleStatus:
        try:
            current = ProviderObservationLifecycleStatus(
                str(row["lifecycle_status"] or ProviderObservationLifecycleStatus.ACTIVE.value)
            )
        except ValueError as exc:
            raise RepositoryError("stored provider observation lifecycle is invalid") from exc
        if current in {
            ProviderObservationLifecycleStatus.INVALIDATED,
            ProviderObservationLifecycleStatus.EXPIRED,
        }:
            return current
        policy_status = self.retention_policy.classify(observation, as_of)
        if current == ProviderObservationLifecycleStatus.STALE and policy_status == ProviderObservationLifecycleStatus.EXPIRED:
            return ProviderObservationLifecycleStatus.EXPIRED
        if current == ProviderObservationLifecycleStatus.ACTIVE and policy_status in {
            ProviderObservationLifecycleStatus.STALE,
            ProviderObservationLifecycleStatus.EXPIRED,
        }:
            return policy_status
        return current

    @staticmethod
    def _insert_lifecycle_event(connection: Any, event: ProviderObservationLifecycleEvent) -> None:
        event.verify()
        payload = event.to_dict()
        connection.execute(
            """
            INSERT INTO provider_observation_lifecycle_events (
                audit_event_id, observation_id, tenant_id, case_id,
                previous_status, new_status, actor_id, correlation_id,
                event_timestamp, reason, event_type, schema_version, event_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["audit_event_id"], payload["observation_id"], payload["tenant_id"],
                payload["case_id"], payload["previous_status"], payload["new_status"],
                payload["actor_id"], payload["correlation_id"], payload["timestamp"],
                payload["reason"], payload["event_type"], payload["schema_version"],
                payload["event_digest"],
            ),
        )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def _row_payload(row: Any) -> dict[str, Any]:
        return {
            "observation_id": row["observation_id"],
            "tenant_id": row["tenant_id"],
            "case_id": row["case_id"],
            "correlation_id": row["correlation_id"],
            "actor_id": row["actor_id"],
            "provider_name": row["provider_name"],
            "provider_version": row["provider_version"],
            "observation_type": row["observation_type"],
            "source": row["source"],
            "source_reference": row["source_reference"],
            "observed_at": row["observed_at"],
            "status": row["status"],
            "normalized_observation": json.loads(row["normalized_observation_json"]),
            "provenance": json.loads(row["provenance_json"]),
            "evidence_references": json.loads(row["evidence_references_json"]),
            "integrity_digest": row["integrity_digest"],
            "schema_version": row["schema_version"],
            "invalidated": bool(row["invalidated"]),
        }

    def save(self, observation: ProviderObservation, *, authorization_context: Any) -> ProviderObservation:
        return self.save_for_tenant(observation.tenant_id, observation, authorization_context=authorization_context)

    def save_for_tenant(self, tenant_id: str, observation: ProviderObservation, *, authorization_context: Any) -> ProviderObservation:
        tenant = str(tenant_id or "").strip()
        if not tenant or not isinstance(observation, ProviderObservation):
            raise RepositoryError("provider observation tenant and contract are required")
        if observation.tenant_id != tenant:
            raise RepositoryError("provider observation tenant ownership is required")
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant,
            actor_id=observation.actor_id,
            correlation_id=observation.correlation_id or "",
            permission="cases.write",
        )
        try:
            observation.verify()
        except ProviderObservationIntegrityError as exc:
            raise RepositoryError("provider observation integrity verification failed") from exc
        payload = observation.to_dict()
        lifecycle = self._lifecycle_fields(observation, self._reference_time())
        try:
            with self.db.session() as connection:
                existing = connection.execute(
                    "SELECT * FROM provider_observations WHERE observation_id=?",
                    (observation.observation_id,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["tenant_id"] != tenant
                        or existing["case_id"] != observation.case_id
                        or existing["integrity_digest"] != observation.integrity_digest
                    ):
                        raise RepositoryError("provider observation identity conflict")
                    try:
                        lifecycle_status = ProviderObservationLifecycleStatus(
                            str(existing["lifecycle_status"] or ProviderObservationLifecycleStatus.ACTIVE.value)
                        )
                    except ValueError as exc:
                        raise RepositoryError("stored provider observation lifecycle is invalid") from exc
                    if lifecycle_status == ProviderObservationLifecycleStatus.INVALIDATED:
                        raise RepositoryError("provider observation is invalidated")
                    if lifecycle_status == ProviderObservationLifecycleStatus.EXPIRED:
                        raise RepositoryError("provider observation is expired")
                    return observation
                connection.execute(
                    """
                    INSERT INTO provider_observations (
                        observation_id, tenant_id, case_id, correlation_id, actor_id,
                        provider_name, provider_version, observation_type, source,
                        source_reference, observed_at, status,
                        normalized_observation_json, provenance_json,
                        evidence_references_json, integrity_digest, schema_version,
                        invalidated, lifecycle_status, lifecycle_updated_at,
                        lifecycle_stale_at, lifecycle_expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["observation_id"], payload["tenant_id"], payload["case_id"],
                        payload["correlation_id"], payload["actor_id"], payload["provider_name"],
                        payload["provider_version"], payload["observation_type"], payload["source"],
                        payload["source_reference"], payload["observed_at"], payload["status"],
                        self._json(payload["normalized_observation"]), self._json(payload["provenance"]),
                        self._json(payload["evidence_references"]), payload["integrity_digest"],
                        payload["schema_version"], 0, lifecycle["status"],
                        lifecycle["updated_at"], lifecycle["stale_at"], lifecycle["expires_at"],
                    ),
                )
            return observation
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Unable to persist provider observation") from exc

    def get_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        correlation_id: str | None = None,
        actor_id: str | None = None,
        authorization_context: Any,
    ) -> ProviderObservation | None:
        tenant = str(tenant_id or "").strip()
        case = str(case_id or "").strip()
        if not tenant or not case or not observation_id:
            return None
        requested_actor = str(actor_id or getattr(authorization_context, "actor_id", "") or "")
        requested_correlation = str(correlation_id or getattr(authorization_context, "correlation_id", "") or "")
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant,
            actor_id=requested_actor,
            correlation_id=requested_correlation,
            permission="investigations.read",
        )
        with self.db.session() as connection:
            row = self._row_for_scope(connection, observation_id, tenant, case, requested_correlation)
        if row is None:
            return None
        try:
            observation = ProviderObservation.from_dict(self._row_payload(row))
        except (KeyError, TypeError, ValueError, ProviderObservationIntegrityError) as exc:
            raise RepositoryError("stored provider observation failed integrity validation") from exc
        if observation.actor_id != requested_actor:
            raise RepositoryError("stored provider observation actor mismatch")
        return observation

    def get_lifecycle_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        correlation_id: str,
        actor_id: str,
        authorization_context: Any,
    ) -> ProviderObservationLifecycleRecord | None:
        """Return safe lifecycle metadata after the existing auth boundary approves."""
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="investigations.read",
        )
        with self.db.session() as connection:
            row = self._row_for_scope(connection, observation_id, str(tenant_id), str(case_id), correlation_id)
        if row is None:
            return None
        observation = self._load_observation(row)
        return self._row_lifecycle(row, observation)

    def get_analyst_records_for_tenant(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        authorization_context: Any,
    ) -> list[tuple[ProviderObservation, ProviderObservationLifecycleRecord, tuple[ProviderObservationLifecycleEvent, ...]]]:
        started = time.perf_counter()
        request_correlation = getattr(authorization_context, "correlation_id", None)
        self._emit_observability(
            "provider_observation_projection_request",
            tenant_id=str(tenant_id or "unknown"),
            correlation_id=str(request_correlation or "unknown"),
            paginated=False,
            page_phase="non_paginated",
            page_size=self.max_projection_observations,
        )
        stats = {"observation_select_count": 0, "lifecycle_event_select_count": 0}
        try:
            page = self._get_analyst_page_for_tenant(
                tenant_id=tenant_id,
                case_id=case_id,
                actor_id=actor_id,
                authorization_context=authorization_context,
                page_size=self.max_projection_observations,
                _stats=stats,
            )
        except Exception as exc:
            self._emit_projection_telemetry(
                "provider_observation_projection_failure",
                started=started,
                tenant_id=tenant_id,
                correlation_id=request_correlation,
                paginated=False,
                page_phase="non_paginated",
                final_page=False,
                page_size=self.max_projection_observations,
                observation_count=0,
                lifecycle_event_count=0,
                has_more=False,
                observation_select_count=stats["observation_select_count"],
                lifecycle_event_select_count=stats["lifecycle_event_select_count"],
                result="rejected",
                error_category=self._projection_error_category(exc),
            )
            raise
        if page.has_more:
            self._emit_projection_telemetry(
                "provider_observation_projection_failure",
                started=started,
                tenant_id=tenant_id,
                correlation_id=request_correlation,
                paginated=False,
                page_phase="non_paginated",
                final_page=False,
                page_size=self.max_projection_observations,
                observation_count=len(page.records),
                lifecycle_event_count=sum(len(record[2]) for record in page.records),
                has_more=True,
                observation_select_count=stats["observation_select_count"],
                lifecycle_event_select_count=stats["lifecycle_event_select_count"],
                result="rejected",
                error_category="projection_bound_exceeded",
            )
            raise ProviderObservationProjectionBoundedError(
                "provider observation analyst projection exceeds observation bound"
            )
        self._emit_projection_telemetry(
            "provider_observation_projection_success",
            started=started,
            tenant_id=tenant_id,
            correlation_id=request_correlation,
            paginated=False,
            page_phase="non_paginated",
            final_page=True,
            page_size=self.max_projection_observations,
            observation_count=len(page.records),
            lifecycle_event_count=sum(len(record[2]) for record in page.records),
            has_more=False,
            observation_select_count=stats["observation_select_count"],
            lifecycle_event_select_count=stats["lifecycle_event_select_count"],
            result="success",
        )
        return list(page.records)

    def get_analyst_page_for_tenant(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        authorization_context: Any,
        page_size: int,
        cursor: str | None = None,
        _paginated: bool = True,
        _emit_telemetry: bool = True,
    ) -> AnalystProjectionPage:
        started = time.perf_counter()
        request_correlation = getattr(authorization_context, "correlation_id", None)
        page_phase = "continuation" if cursor is not None else "first"
        stats = {"observation_select_count": 0, "lifecycle_event_select_count": 0}
        if _emit_telemetry:
            self._emit_observability(
                "provider_observation_projection_request",
                tenant_id=str(tenant_id or "unknown"),
                correlation_id=str(request_correlation or "unknown"),
                paginated=_paginated,
                page_phase=page_phase,
                page_size=page_size if isinstance(page_size, int) and not isinstance(page_size, bool) else None,
            )
        try:
            page = self._get_analyst_page_for_tenant(
                tenant_id=tenant_id,
                case_id=case_id,
                actor_id=actor_id,
                authorization_context=authorization_context,
                page_size=page_size,
                cursor=cursor,
                _stats=stats,
            )
        except Exception as exc:
            if _emit_telemetry:
                self._emit_projection_telemetry(
                    "provider_observation_projection_failure",
                    started=started,
                    tenant_id=tenant_id,
                    correlation_id=request_correlation,
                    paginated=_paginated,
                    page_phase=page_phase,
                    final_page=False,
                    page_size=page_size if isinstance(page_size, int) and not isinstance(page_size, bool) else None,
                    observation_count=0,
                    lifecycle_event_count=0,
                    has_more=False,
                    observation_select_count=stats["observation_select_count"],
                    lifecycle_event_select_count=stats["lifecycle_event_select_count"],
                    result="rejected",
                    error_category=self._projection_error_category(exc),
                )
            raise
        if _emit_telemetry:
            self._emit_projection_telemetry(
                "provider_observation_projection_success",
                started=started,
                tenant_id=tenant_id,
                correlation_id=request_correlation,
                paginated=_paginated,
                page_phase=page_phase,
                final_page=not page.has_more,
                page_size=page.page_size,
                observation_count=len(page.records),
                lifecycle_event_count=sum(len(record[2]) for record in page.records),
                has_more=page.has_more,
                observation_select_count=stats["observation_select_count"],
                lifecycle_event_select_count=stats["lifecycle_event_select_count"],
                result="success",
            )
        return page

    def _get_analyst_page_for_tenant(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        authorization_context: Any,
        page_size: int,
        cursor: str | None = None,
        _stats: dict[str, int] | None = None,
    ) -> AnalystProjectionPage:
        """Return authorized, case-scoped records for the analyst projection.

        Authorization is evaluated once against the trusted request context.  The
        two scoped queries avoid one query per observation while keeping raw
        ProviderObservation objects inside the repository-to-projection boundary.
        Callers must not serialize this internal result directly.
        """
        request_correlation = getattr(authorization_context, "correlation_id", None)
        if not request_correlation:
            raise PermissionError("provider observation lifecycle correlation is required")
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=str(tenant_id),
            actor_id=str(actor_id),
            correlation_id=str(request_correlation),
            permission="investigations.read",
        )
        requested_page_size = self._validate_page_size(page_size)
        last_observation_id = None
        if cursor is not None:
            last_observation_id, requested_page_size = self._decode_cursor(
                cursor,
                tenant_id=str(tenant_id),
                case_id=str(case_id),
                actor_id=str(actor_id),
                correlation_id=str(request_correlation),
                page_size=requested_page_size,
            )
        tenant = str(tenant_id or "").strip()
        case = str(case_id or "").strip()
        if not tenant or not case:
            return self.AnalystProjectionPage((), requested_page_size, False, None)
        with self.db.session() as connection:
            scope_predicate = "tenant_id=? AND case_id=?"
            scope_params: tuple[Any, ...] = (tenant, case)
            if last_observation_id is not None:
                scope_predicate += " AND observation_id > ?"
                scope_params += (last_observation_id,)
            observation_rows = connection.execute(
                f"""
                SELECT * FROM provider_observations
                WHERE {scope_predicate}
                ORDER BY observation_id ASC
                LIMIT ?
                """,
                (*scope_params, requested_page_size + 1),
            ).fetchall()
            if _stats is not None:
                _stats["observation_select_count"] += 1
            has_more = len(observation_rows) > requested_page_size
            observation_rows = observation_rows[:requested_page_size]

            observation_ids = [str(row["observation_id"]) for row in observation_rows]
            audit_rows = []
            for offset in range(0, len(observation_ids), 500):
                chunk = observation_ids[offset : offset + 500]
                placeholders = ",".join("?" for _ in chunk)
                remaining = self.max_projection_events - len(audit_rows)
                if remaining <= 0:
                    raise ProviderObservationProjectionBoundedError(
                        "provider observation analyst projection exceeds lifecycle-event bound"
                    )
                audit_rows.extend(
                    connection.execute(
                        f"""
                        SELECT * FROM provider_observation_lifecycle_events
                        WHERE tenant_id=? AND case_id=?
                          AND observation_id IN ({placeholders})
                        ORDER BY observation_id ASC, event_timestamp ASC, audit_event_id ASC
                        LIMIT ?
                        """,
                        (tenant, case, *chunk, remaining + 1),
                    ).fetchall()
                )
                if _stats is not None:
                    _stats["lifecycle_event_select_count"] += 1
                if len(audit_rows) > self.max_projection_events:
                    raise ProviderObservationProjectionBoundedError(
                        "provider observation analyst projection exceeds lifecycle-event bound"
                    )

        events_by_observation: dict[str, list[ProviderObservationLifecycleEvent]] = {}
        for row in audit_rows:
            try:
                event = ProviderObservationLifecycleEvent.from_dict(
                    {
                        "audit_event_id": row["audit_event_id"],
                        "observation_id": row["observation_id"],
                        "tenant_id": row["tenant_id"],
                        "case_id": row["case_id"],
                        "previous_status": row["previous_status"],
                        "new_status": row["new_status"],
                        "actor_id": row["actor_id"],
                        "correlation_id": row["correlation_id"],
                        "timestamp": row["event_timestamp"],
                        "reason": row["reason"],
                        "event_type": row["event_type"],
                        "schema_version": row["schema_version"],
                        "event_digest": row["event_digest"],
                    }
                )
            except (KeyError, TypeError, ValueError, ProviderObservationLifecycleError) as exc:
                raise RepositoryError("stored provider observation lifecycle audit is invalid") from exc
            events_by_observation.setdefault(event.observation_id, []).append(event)

        records = []
        for row in observation_rows:
            observation = self._load_observation(row)
            effective_status = self._effective_status(row, observation, self._reference_time())
            lifecycle = self._row_lifecycle(row, observation)
            if lifecycle.status != effective_status.value:
                lifecycle = replace(lifecycle, status=effective_status.value)
            records.append(
                (
                    observation,
                    lifecycle,
                    tuple(events_by_observation.get(observation.observation_id, ())),
                )
            )
        next_cursor = None
        if has_more and records:
            next_cursor = self._encode_cursor(
                tenant_id=tenant,
                case_id=case,
                actor_id=str(actor_id),
                correlation_id=str(request_correlation),
                page_size=requested_page_size,
                last_observation_id=records[-1][0].observation_id,
            )
        return self.AnalystProjectionPage(
            tuple(records),
            requested_page_size,
            has_more,
            next_cursor,
        )

    def resolve_for_replay(
        self,
        observation_ids: Iterable[str],
        *,
        tenant_id: str,
        case_id: str,
        correlation_id: str | None = None,
        actor_id: str | None = None,
        authorization_context: Any,
    ) -> list[ProviderObservation]:
        started = time.perf_counter()
        requested_actor = str(actor_id or getattr(authorization_context, "actor_id", "") or "")
        requested_correlation = str(correlation_id or getattr(authorization_context, "correlation_id", "") or "")
        references: list[str] = []
        batch_count = 0
        self._replay_observability(
            "replay_requests",
            started=started,
            tenant_id=tenant_id,
            correlation_id=requested_correlation,
            observation_count=0,
            batch_count=0,
            result="started",
        )
        try:
            self._authorize_lifecycle(
                authorization_context=authorization_context,
                tenant_id=str(tenant_id),
                actor_id=requested_actor,
                correlation_id=requested_correlation,
                permission="investigations.read",
            )
            try:
                raw_references = list(observation_ids)
            except TypeError as exc:
                raise RepositoryError("provider observation replay reference is malformed") from exc
            for value in raw_references:
                if not isinstance(value, str) or not re.fullmatch(r"PO-[0-9a-f]{24}", value):
                    raise RepositoryError("provider observation replay reference is malformed")
                references.append(value)
            if len(set(references)) != len(references):
                raise RepositoryError("provider observation replay references are duplicated")

            rows_by_id: dict[str, Any] = {}
            tenant = str(tenant_id)
            case = str(case_id)
            for offset in range(0, len(references), self.replay_batch_size):
                batch = references[offset : offset + self.replay_batch_size]
                if not batch:
                    continue
                placeholders = ",".join("?" for _ in batch)
                with self.db.session() as connection:
                    rows = connection.execute(
                        f"""
                        SELECT * FROM provider_observations
                        WHERE tenant_id=? AND case_id=?
                          AND observation_id IN ({placeholders})
                        """,
                        (tenant, case, *batch),
                    ).fetchall()
                batch_count += 1
                for row in rows:
                    observation_id = str(row["observation_id"])
                    if row["correlation_id"] != requested_correlation:
                        continue
                    rows_by_id[observation_id] = row

            if any(reference not in rows_by_id for reference in references):
                raise RepositoryError("required provider observation is unavailable")

            resolved: list[ProviderObservation] = []
            for reference in references:
                row = rows_by_id[reference]
                observation = self._load_observation(row)
                if observation.actor_id != requested_actor:
                    raise RepositoryError("stored provider observation actor mismatch")
                effective_status = self._effective_status(row, observation, self._reference_time())
                if effective_status == ProviderObservationLifecycleStatus.INVALIDATED:
                    raise RepositoryError("provider observation replay is not eligible: invalidated")
                if effective_status == ProviderObservationLifecycleStatus.EXPIRED:
                    raise RepositoryError("provider observation replay is not eligible: expired")
                # STALE is explicitly replayable for historical investigations. It
                # is never refreshed from a provider and remains visibly stale in
                # the normalized provider status.
                resolved.append(observation)
            if [item.observation_id for item in resolved] != references:
                raise RepositoryError("provider observation replay ordering is invalid")
        except Exception as exc:
            event = self._replay_failure_event(exc)
            self._replay_observability(
                event,
                started=started,
                tenant_id=tenant_id,
                correlation_id=requested_correlation,
                observation_count=len(references),
                batch_count=batch_count,
                result="rejected",
            )
            self._replay_observability(
                "replay_duration",
                started=started,
                tenant_id=tenant_id,
                correlation_id=requested_correlation,
                observation_count=len(references),
                batch_count=batch_count,
                result="rejected",
            )
            raise
        self._replay_observability(
            "replay_success",
            started=started,
            tenant_id=tenant_id,
            correlation_id=requested_correlation,
            observation_count=len(resolved),
            batch_count=batch_count,
            result="success",
        )
        self._replay_observability(
            "replay_duration",
            started=started,
            tenant_id=tenant_id,
            correlation_id=requested_correlation,
            observation_count=len(resolved),
            batch_count=batch_count,
            result="success",
        )
        self._replay_observability(
            "provider_execution_avoided",
            started=started,
            tenant_id=tenant_id,
            correlation_id=requested_correlation,
            observation_count=len(resolved),
            batch_count=batch_count,
            result="success",
        )
        return resolved

    def get_by_case_id_for_tenant(self, case_id: str, tenant_id: str, *, actor_id: str, correlation_id: str, authorization_context: Any) -> list[ProviderObservation]:
        tenant = str(tenant_id or "").strip()
        case = str(case_id or "").strip()
        if not tenant or not case:
            return []
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="investigations.read",
        )
        with self.db.session() as connection:
            rows = connection.execute(
                """
                SELECT * FROM provider_observations
                WHERE tenant_id=? AND case_id=?
                  AND correlation_id=? AND actor_id=?
                ORDER BY observation_id
                """,
                (tenant, case, correlation_id, actor_id),
            ).fetchall()
        result = []
        for row in rows:
            try:
                result.append(ProviderObservation.from_dict(self._row_payload(row)))
            except (KeyError, TypeError, ValueError, ProviderObservationIntegrityError) as exc:
                raise RepositoryError("stored provider observation failed integrity validation") from exc
        return result

    def _transition_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
        target_status: ProviderObservationLifecycleStatus,
        reason: str,
        event_type: str,
        as_of: datetime | None = None,
        current_status: ProviderObservationLifecycleStatus | None = None,
    ) -> ProviderObservationLifecycleRecord:
        started = time.perf_counter()
        state = {"target_status": target_status.value}
        with self._observe_lifecycle_transition(
            started=started,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            state=state,
        ):
            result = self._transition_for_tenant_unobserved(
                observation_id,
                tenant_id=tenant_id,
                case_id=case_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                authorization_context=authorization_context,
                target_status=target_status,
                reason=reason,
                event_type=event_type,
                as_of=as_of,
                current_status=current_status,
            )
            state["resulting_status"] = result.status
            return result

    def _transition_for_tenant_unobserved(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
        target_status: ProviderObservationLifecycleStatus,
        reason: str,
        event_type: str,
        as_of: datetime | None = None,
        current_status: ProviderObservationLifecycleStatus | None = None,
    ) -> ProviderObservationLifecycleRecord:
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="cases.write",
        )
        reference_time = self._reference_time(as_of)
        timestamp = self._timestamp(reference_time)
        with self._lifecycle_session() as connection:
            row = self._row_for_scope(
                connection,
                observation_id,
                str(tenant_id),
                str(case_id),
                correlation_id,
            )
            if row is None:
                raise RepositoryError("provider observation was not found")
            observation = self._load_observation(row)
            try:
                stored_current = ProviderObservationLifecycleStatus(
                    str(row["lifecycle_status"] or ProviderObservationLifecycleStatus.ACTIVE.value)
                )
            except ValueError as exc:
                raise RepositoryError("stored provider observation lifecycle is invalid") from exc
            current = current_status or self._effective_status(row, observation, reference_time)
            if current == target_status and stored_current != target_status:
                current = stored_current
            allowed = {
                ProviderObservationLifecycleStatus.ACTIVE: {
                    ProviderObservationLifecycleStatus.STALE,
                    ProviderObservationLifecycleStatus.INVALIDATED,
                    ProviderObservationLifecycleStatus.EXPIRED,
                },
                ProviderObservationLifecycleStatus.STALE: {
                    ProviderObservationLifecycleStatus.INVALIDATED,
                    ProviderObservationLifecycleStatus.EXPIRED,
                },
                ProviderObservationLifecycleStatus.INVALIDATED: set(),
                ProviderObservationLifecycleStatus.EXPIRED: set(),
            }
            if target_status not in allowed[current]:
                raise ProviderObservationLifecycleError(
                    f"invalid provider observation lifecycle transition: {current.value} to {target_status.value}"
                )
            if target_status == ProviderObservationLifecycleStatus.EXPIRED:
                policy_status = self.retention_policy.classify(observation, reference_time)
                if policy_status != ProviderObservationLifecycleStatus.EXPIRED:
                    raise ProviderObservationLifecycleError("provider observation retention boundary has not been reached")
            lifecycle = self._lifecycle_fields(observation, reference_time)
            update = connection.execute(
                """
                UPDATE provider_observations
                SET lifecycle_status=?, lifecycle_updated_at=?,
                    lifecycle_stale_at=?, lifecycle_expires_at=?,
                    lifecycle_invalidated_at=?, lifecycle_invalidated_by=?,
                    lifecycle_invalidation_reason=?
                WHERE observation_id=? AND tenant_id=? AND case_id=?
                  AND lifecycle_status=?
                """,
                (
                    target_status.value,
                    timestamp,
                    lifecycle["stale_at"],
                    lifecycle["expires_at"],
                    timestamp if target_status == ProviderObservationLifecycleStatus.INVALIDATED else row["lifecycle_invalidated_at"],
                    actor_id if target_status == ProviderObservationLifecycleStatus.INVALIDATED else row["lifecycle_invalidated_by"],
                    reason if target_status == ProviderObservationLifecycleStatus.INVALIDATED else row["lifecycle_invalidation_reason"],
                    observation_id,
                    tenant_id,
                    case_id,
                    current_status.value if current_status is not None else stored_current.value,
                ),
            )
            if update.rowcount != 1:
                raise ProviderObservationLifecycleError("provider observation lifecycle conflict")
            event = ProviderObservationLifecycleEvent.create(
                observation_id=observation.observation_id,
                tenant_id=observation.tenant_id,
                case_id=observation.case_id,
                previous_status=current.value,
                new_status=target_status.value,
                actor_id=actor_id,
                correlation_id=correlation_id,
                timestamp=reference_time,
                reason=reason,
                event_type=event_type,
            )
            self._insert_lifecycle_event(connection, event)
            updated_row = self._row_for_scope(connection, observation_id, str(tenant_id), str(case_id), correlation_id)
            if updated_row is None:
                raise RepositoryError("provider observation lifecycle update was not persisted")
            return self._row_lifecycle(updated_row, observation)

    def invalidate_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
        reason: str,
        as_of: datetime | None = None,
    ) -> ProviderObservationLifecycleRecord:
        """Authorize and explicitly transition an observation to INVALIDATED."""
        return self._transition_for_tenant(
            observation_id,
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            authorization_context=authorization_context,
            target_status=ProviderObservationLifecycleStatus.INVALIDATED,
            reason=reason,
            event_type="PROVIDER_OBSERVATION_INVALIDATED",
            as_of=as_of,
        )

    def refresh_lifecycle_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
        reason: str = "retention policy lifecycle evaluation",
        as_of: datetime | None = None,
    ) -> ProviderObservationLifecycleRecord:
        """Apply one deterministic policy transition; never refresh provider data."""
        reference_time = self._reference_time(as_of)
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="cases.write",
        )
        with self.db.session() as connection:
            row = self._row_for_scope(connection, observation_id, str(tenant_id), str(case_id), correlation_id)
        if row is None:
            raise RepositoryError("provider observation was not found")
        observation = self._load_observation(row)
        try:
            current = ProviderObservationLifecycleStatus(
                str(row["lifecycle_status"] or ProviderObservationLifecycleStatus.ACTIVE.value)
            )
        except ValueError as exc:
            raise RepositoryError("stored provider observation lifecycle is invalid") from exc
        target = self.retention_policy.classify(observation, reference_time)
        if current in {
            ProviderObservationLifecycleStatus.INVALIDATED,
            ProviderObservationLifecycleStatus.EXPIRED,
        } or target == current or target == ProviderObservationLifecycleStatus.ACTIVE:
            return self._row_lifecycle(row, observation)
        return self._transition_for_tenant(
            observation_id,
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            authorization_context=authorization_context,
            target_status=target,
            reason=reason,
            event_type="PROVIDER_OBSERVATION_LIFECYCLE_REFRESHED",
            as_of=reference_time,
            current_status=current,
        )

    def expire_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
        reason: str = "retention policy expiration",
        as_of: datetime | None = None,
    ) -> ProviderObservationLifecycleRecord:
        """Explicitly apply retention expiration; no background worker is created."""
        return self._transition_for_tenant(
            observation_id,
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            authorization_context=authorization_context,
            target_status=ProviderObservationLifecycleStatus.EXPIRED,
            reason=reason,
            event_type="PROVIDER_OBSERVATION_EXPIRED",
            as_of=as_of,
        )

    def get_lifecycle_events_for_tenant(
        self,
        *,
        observation_id: str,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
    ) -> list[ProviderObservationLifecycleEvent]:
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="investigations.read",
        )
        with self.db.session() as connection:
            rows = connection.execute(
                """
                SELECT * FROM provider_observation_lifecycle_events
                WHERE observation_id=? AND tenant_id=? AND case_id=?
                  AND correlation_id=?
                ORDER BY event_timestamp ASC, audit_event_id ASC
                """,
                (str(observation_id), str(tenant_id), str(case_id), str(correlation_id)),
            ).fetchall()
        events: list[ProviderObservationLifecycleEvent] = []
        for row in rows:
            try:
                event = ProviderObservationLifecycleEvent.from_dict(
                    {
                        "audit_event_id": row["audit_event_id"],
                        "observation_id": row["observation_id"],
                        "tenant_id": row["tenant_id"],
                        "case_id": row["case_id"],
                        "previous_status": row["previous_status"],
                        "new_status": row["new_status"],
                        "actor_id": row["actor_id"],
                        "correlation_id": row["correlation_id"],
                        "timestamp": row["event_timestamp"],
                        "reason": row["reason"],
                        "event_type": row["event_type"],
                        "schema_version": row["schema_version"],
                        "event_digest": row["event_digest"],
                    }
                )
            except (KeyError, TypeError, ValueError, ProviderObservationLifecycleError) as exc:
                raise RepositoryError("stored provider observation lifecycle audit is invalid") from exc
            events.append(event)
        return events

    def delete_for_tenant(
        self,
        observation_id: str,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str,
        authorization_context: Any,
    ) -> None:
        self._authorize_lifecycle(
            authorization_context=authorization_context,
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            permission="cases.write",
        )
        with self.db.session() as connection:
            updated = connection.execute(
                """
                DELETE FROM provider_observations
                WHERE observation_id=? AND tenant_id=? AND case_id=?
                """,
                (str(observation_id), str(tenant_id), str(case_id)),
            ).rowcount
        if not updated:
            raise RepositoryError("provider observation was not found")
