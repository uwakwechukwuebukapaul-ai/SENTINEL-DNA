"""Authorized durable alert intake for the V2.1 investigation runtime.

This module is the secure front door to ``InvestigationJob``.  It normalizes a
small, secret-free alert projection, binds it to an authenticated tenant and
actor, applies a conservative eligibility policy, and persists the trigger and
queued job.  It never invokes the worker or the investigation coordinator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Mapping
from uuid import uuid4

from services.audit.service import AuditService
from services.intelligence.repository.execution_repository import (
    ExecutionRepository,
    JobConflictError,
)
from services.intelligence.runtime.investigation_job import InvestigationJob


WRITE_ROLES = frozenset({"admin", "soc_manager", "analyst"})
ALLOWED_SOURCES = frozenset({"api", "detection", "windows", "linux", "syslog", "generic"})
BLOCKED_CAPABILITIES = frozenset({
    "remediation", "containment", "credential_reset", "session_revocation",
    "host_isolation", "blocking", "destructive_action",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, field_name: str, *, required: bool = False, limit: int = 256) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field_name}_required")
        return None
    text = str(value).strip()
    if not text and required:
        raise ValueError(f"{field_name}_required")
    if len(text) > limit or any(ord(char) < 32 for char in text):
        raise ValueError(f"{field_name}_invalid")
    return text or None


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]}"


@dataclass(frozen=True)
class EligibilityDecision:
    outcome: str
    reason: str


@dataclass
class InvestigationTrigger:
    trigger_id: str
    tenant_id: str
    source: str
    source_event_id: str
    actor_id: str | None
    service_identity: str | None
    correlation_id: str
    idempotency_key: str
    received_at: str
    normalized_at: str | None
    authorization_result: str
    eligibility_result: str
    rejection_reason: str | None
    job_id: str | None
    payload_digest: str
    normalized_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, name in (
            (self.trigger_id, "trigger_id"), (self.tenant_id, "tenant_id"),
            (self.source, "source"), (self.source_event_id, "source_event_id"),
            (self.correlation_id, "correlation_id"),
            (self.idempotency_key, "idempotency_key"),
            (self.payload_digest, "payload_digest"),
        ):
            _safe_text(value, name, required=True)
        if not self.actor_id and not self.service_identity:
            raise PermissionError("actor or service identity is required")
        if self.authorization_result not in {"AUTHORIZED", "REJECTED", "BLOCKED"}:
            raise ValueError("authorization_result_invalid")
        if self.eligibility_result not in {"ELIGIBLE", "INELIGIBLE", "BLOCKED"}:
            raise ValueError("eligibility_result_invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "tenant_id": self.tenant_id,
            "source": self.source,
            "source_event_id": self.source_event_id,
            "actor_id": self.actor_id,
            "service_identity": self.service_identity,
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
            "received_at": self.received_at,
            "normalized_at": self.normalized_at,
            "authorization_result": self.authorization_result,
            "eligibility_result": self.eligibility_result,
            "rejection_reason": self.rejection_reason,
            "job_id": self.job_id,
            "payload_digest": self.payload_digest,
            "normalized_payload": dict(self.normalized_payload),
        }


@dataclass(frozen=True)
class InvestigationIntakeResult:
    accepted: bool
    duplicate: bool
    status: str
    code: str
    reason: str
    trigger_id: str
    job_id: str | None
    state: str | None
    correlation_id: str
    http_status: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "duplicate": self.duplicate,
            "status": self.status,
            "code": self.code,
            "reason": self.reason,
            "trigger_id": self.trigger_id,
            "job_id": self.job_id,
            "state": self.state,
            "correlation_id": self.correlation_id,
        }


class InvestigationIntake:
    """Tenant-bound, idempotent, non-executing durable alert intake."""

    def __init__(
        self,
        repository: ExecutionRepository,
        *,
        audit_service: AuditService | None = None,
        eligibility_policy: Callable[[dict[str, Any]], EligibilityDecision] | None = None,
        authorize_service_identity: Callable[[str], bool] | None = None,
    ) -> None:
        if not isinstance(repository, ExecutionRepository):
            raise TypeError("repository must be an ExecutionRepository")
        self.repository = repository
        self.audit_service = audit_service or repository.audit_service
        self.eligibility_policy = eligibility_policy or self._default_eligibility
        self.authorize_service_identity = authorize_service_identity or (lambda identity: False)

    def accept(
        self,
        payload: Mapping[str, Any] | None,
        *,
        context: Any | None = None,
        source: str = "api",
        idempotency_key: str | None = None,
        service_identity: str | None = None,
    ) -> InvestigationIntakeResult:
        context = context or self._request_context()
        correlation_id = _safe_text(getattr(context, "correlation_id", None), "correlation_id") or str(uuid4())
        trigger_id = _stable_id("trg", f"{correlation_id}:{uuid4()}")
        tenant_id = _safe_text(getattr(context, "tenant_id", None), "tenant_id")
        actor_id = _safe_text(getattr(context, "actor_id", None) or getattr(context, "user_id", None), "actor_id")
        service_identity = _safe_text(service_identity, "service_identity")

        if getattr(context, "error", None):
            return self._blocked(
                payload, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code=str(context.error), reason="authenticated security context is not valid",
            )
        if not tenant_id:
            return self._blocked(
                payload, tenant_id=None, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="tenant_required", reason="authenticated tenant context is required",
            )
        if not actor_id and not service_identity:
            return self._blocked(
                payload, tenant_id=tenant_id, actor_id=None, service_identity=None,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="actor_or_service_identity_required", reason="authorized actor or service identity is required",
            )
        if service_identity and not self.authorize_service_identity(service_identity):
            return self._blocked(
                payload, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="service_identity_unauthorized", reason="service identity is not authorized for intake",
            )
        if actor_id and not set(getattr(context, "roles", ()) or ()).intersection(WRITE_ROLES):
            return self._blocked(
                payload, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="intake_unauthorized", reason="actor is not authorized for durable intake",
            )

        try:
            normalized = self.normalize_alert(payload, tenant_id=tenant_id, source=source)
        except ValueError as exc:
            return self._blocked(
                payload, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="malformed_alert", reason=str(exc),
            )

        derived_key = f"{normalized['source']}:{normalized['source_event_id']}"
        if idempotency_key and str(idempotency_key) != derived_key:
            return self._blocked(
                normalized, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                code="idempotency_key_mismatch", reason="idempotency must bind to source event identity",
            )
        canonical_key = derived_key
        payload_digest = _digest(normalized)
        existing = self.repository.get_trigger_by_idempotency_key(canonical_key, tenant_id)
        if existing is not None:
            if existing.payload_digest != payload_digest:
                self._audit(existing, "idempotency_conflict", {"payload_digest": payload_digest})
                return InvestigationIntakeResult(
                    accepted=False, duplicate=False, status="BLOCKED", code="idempotency_conflict",
                    reason="source event identity is already bound to different alert content",
                    trigger_id=existing.trigger_id, job_id=existing.job_id,
                    state=None, correlation_id=correlation_id, http_status=409,
                )
            self._audit(existing, "idempotency_checked", {"payload_digest": payload_digest})
            self._audit(existing, "idempotency_duplicate", {"job_id": existing.job_id})
            existing_job = self.repository.get_job(existing.job_id, tenant_id) if existing.job_id else None
            return InvestigationIntakeResult(
                accepted=existing.eligibility_result == "ELIGIBLE",
                duplicate=True,
                status="ACCEPTED" if existing.eligibility_result == "ELIGIBLE" else existing.eligibility_result,
                code="duplicate" if existing.job_id else "duplicate_rejected",
                reason="existing durable intake returned idempotently",
                trigger_id=existing.trigger_id, job_id=existing.job_id,
                state=existing_job.state.value if existing_job else None,
                correlation_id=existing.correlation_id, http_status=200 if existing.job_id else 422,
            )

        decision = self.eligibility_policy(normalized)
        if not isinstance(decision, EligibilityDecision):
            raise TypeError("eligibility policy must return EligibilityDecision")
        self._audit_unbound_or_bound(
            tenant_id, trigger_id, actor_id, service_identity, correlation_id,
            "trigger_received", {"source": normalized["source"], "source_event_id": normalized["source_event_id"]},
        )
        self._audit_unbound_or_bound(
            tenant_id, trigger_id, actor_id, service_identity, correlation_id,
            "trigger_normalized", {"payload_digest": payload_digest},
        )
        self._audit_unbound_or_bound(
            tenant_id, trigger_id, actor_id, service_identity, correlation_id,
            "intake_authorized", {"authorization_result": "AUTHORIZED"},
        )
        self._audit_unbound_or_bound(
            tenant_id, trigger_id, actor_id, service_identity, correlation_id,
            "eligibility_evaluated", {"eligibility_result": decision.outcome, "reason": decision.reason},
        )

        if decision.outcome != "ELIGIBLE":
            trigger = self._make_trigger(
                normalized, tenant_id, actor_id, service_identity, correlation_id,
                trigger_id, canonical_key, payload_digest, "AUTHORIZED", decision.outcome,
                decision.reason, None,
            )
            try:
                stored, duplicate = self.repository.create_trigger(trigger)
            except JobConflictError:
                return self._blocked(
                    normalized, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                    source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                    code="idempotency_conflict", reason="trigger identity is already bound to another alert",
                )
            self._audit(stored, "investigation_intake_blocked", {"reason": decision.reason})
            return InvestigationIntakeResult(
                accepted=False, duplicate=duplicate, status=decision.outcome,
                code="ineligible_alert" if decision.outcome == "INELIGIBLE" else "intake_blocked",
                reason=decision.reason, trigger_id=stored.trigger_id, job_id=None,
                state=None, correlation_id=stored.correlation_id, http_status=422 if decision.outcome == "INELIGIBLE" else 403,
            )

        job_id = _stable_id("job", f"{tenant_id}:{canonical_key}")
        trigger = self._make_trigger(
            normalized, tenant_id, actor_id, service_identity, correlation_id,
            trigger_id, canonical_key, payload_digest, "AUTHORIZED", "ELIGIBLE", None, job_id,
        )
        job = InvestigationJob(
            job_id=job_id, tenant_id=tenant_id, case_id=normalized["case_id"],
            investigation_id=normalized["investigation_id"], execution_id=_stable_id("exe", job_id),
            trigger_id=trigger_id, idempotency_key=canonical_key,
            actor_id=actor_id, service_identity=service_identity,
            correlation_id=correlation_id, priority=self._priority(normalized["severity"]),
        )
        try:
            stored_trigger, stored_job, duplicate = self.repository.create_trigger_and_job(trigger, job)
        except JobConflictError:
            existing = self.repository.get_trigger_by_idempotency_key(canonical_key, tenant_id)
            if existing is None or existing.payload_digest != payload_digest:
                return self._blocked(
                    normalized, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                    source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                    code="idempotency_conflict", reason="trigger identity is already bound to another alert",
                )
            stored_trigger = existing
            stored_job = self.repository.get_job(existing.job_id, tenant_id)
            if stored_job is None:
                return self._blocked(
                    normalized, tenant_id=tenant_id, actor_id=actor_id, service_identity=service_identity,
                    source=source, correlation_id=correlation_id, trigger_id=trigger_id,
                    code="durable_job_unavailable", reason="existing trigger has no available durable job",
                )
            duplicate = True
        self._audit(stored_trigger, "idempotency_checked", {"payload_digest": payload_digest})
        if duplicate:
            self._audit(stored_trigger, "idempotency_duplicate", {"job_id": stored_job.job_id})
            return InvestigationIntakeResult(
                accepted=True, duplicate=True, status="ACCEPTED", code="duplicate",
                reason="existing durable job returned idempotently", trigger_id=stored_trigger.trigger_id,
                job_id=stored_job.job_id, state=stored_job.state.value,
                correlation_id=stored_trigger.correlation_id, http_status=200,
            )
        self._audit(stored_trigger, "investigation_job_created", {"job_id": stored_job.job_id})
        return InvestigationIntakeResult(
            accepted=True, duplicate=False, status="ACCEPTED", code="accepted",
            reason="alert accepted into durable investigation queue", trigger_id=stored_trigger.trigger_id,
            job_id=stored_job.job_id, state=stored_job.state.value,
            correlation_id=stored_trigger.correlation_id, http_status=202,
        )

    @staticmethod
    def normalize_alert(payload: Mapping[str, Any] | None, *, tenant_id: str, source: str) -> dict[str, Any]:
        payload = dict(payload or {})
        nested = payload.get("alert") if isinstance(payload.get("alert"), Mapping) else {}
        raw: dict[str, Any] = dict(nested)
        raw.update({key: value for key, value in payload.items() if key != "alert"})
        supplied_tenant = raw.get("tenant_id")
        if supplied_tenant is not None and str(supplied_tenant) != str(tenant_id):
            raise ValueError("tenant_context_conflict")
        outer_case = payload.get("case_id")
        nested_case = nested.get("case_id") if isinstance(nested, Mapping) else None
        if outer_case and nested_case and str(outer_case) != str(nested_case):
            raise ValueError("case_context_conflict")
        case_id = _safe_text(outer_case or nested_case, "case_id", required=True)
        event_id = _safe_text(
            raw.get("source_event_id") or raw.get("event_id") or raw.get("alert_id") or raw.get("id"),
            "source_event_id", required=True,
        )
        source_value = _safe_text(source or raw.get("source") or "generic", "source", required=True)
        if source_value not in ALLOWED_SOURCES:
            raise ValueError("unsupported_alert_source")
        investigation_id = _safe_text(raw.get("investigation_id") or case_id, "investigation_id", required=True)
        alert_type = _safe_text(
            raw.get("alert_type") or raw.get("type") or raw.get("event_type") or raw.get("rule_name") or "detection_alert",
            "alert_type", required=True,
        )
        severity = (_safe_text(raw.get("severity") or "MEDIUM", "severity", required=True) or "MEDIUM").upper()
        normalized: dict[str, Any] = {
            "case_id": case_id,
            "investigation_id": investigation_id,
            "source": source_value,
            "source_event_id": event_id,
            "severity": severity,
            "alert_type": alert_type,
        }
        timestamp = raw.get("timestamp") or raw.get("created_at")
        if timestamp is not None:
            normalized["timestamp"] = _safe_text(timestamp, "timestamp", required=True)
        for target, candidates in {
            "title": ("title", "rule_name"),
            "description": ("description", "message"),
        }.items():
            value = next((raw.get(key) for key in candidates if raw.get(key) is not None), None)
            if value is not None:
                normalized[target] = _safe_text(value, target, limit=512)
        refs = raw.get("evidence_references") or raw.get("evidence_refs") or []
        normalized["evidence_references"] = InvestigationIntake._references(refs)
        ioc_refs = raw.get("ioc_references") or raw.get("ioc_refs") or []
        normalized["ioc_references"] = InvestigationIntake._references(ioc_refs)
        if any(str(raw.get(key) or "").lower() in BLOCKED_CAPABILITIES for key in ("action", "capability", "requested_action")):
            normalized["requested_capability"] = "blocked_destructive_capability"
        return normalized

    @staticmethod
    def _references(value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("references_must_be_list")
        output: list[str] = []
        for item in value[:100]:
            candidate = item if isinstance(item, str) else (item.get("evidence_id") or item.get("ioc_id") or item.get("reference") or item.get("id")) if isinstance(item, Mapping) else None
            text = _safe_text(candidate, "reference")
            if text:
                output.append(text)
        return output

    @staticmethod
    def _default_eligibility(normalized: dict[str, Any]) -> EligibilityDecision:
        if normalized.get("requested_capability") == "blocked_destructive_capability":
            return EligibilityDecision("BLOCKED", "destructive capability is not permitted at intake")
        if not normalized.get("case_id") or not normalized.get("source_event_id"):
            return EligibilityDecision("INELIGIBLE", "case and source event identity are required")
        return EligibilityDecision("ELIGIBLE", "alert satisfies durable intake policy")

    @staticmethod
    def _priority(severity: str) -> str:
        value = str(severity or "").lower()
        return "critical" if value == "critical" else "high" if value == "high" else "normal"

    @staticmethod
    def _request_context() -> Any:
        from services.core.security_context import request_context
        return request_context()

    @staticmethod
    def _make_trigger(
        normalized: dict[str, Any], tenant_id: str, actor_id: str | None,
        service_identity: str | None, correlation_id: str, trigger_id: str,
        idempotency_key: str, payload_digest: str, authorization_result: str,
        eligibility_result: str, rejection_reason: str | None, job_id: str | None,
    ) -> InvestigationTrigger:
        return InvestigationTrigger(
            trigger_id=trigger_id, tenant_id=tenant_id, source=normalized["source"],
            source_event_id=normalized["source_event_id"], actor_id=actor_id,
            service_identity=service_identity, correlation_id=correlation_id,
            idempotency_key=idempotency_key, received_at=_now(), normalized_at=_now(),
            authorization_result=authorization_result, eligibility_result=eligibility_result,
            rejection_reason=rejection_reason, job_id=job_id, payload_digest=payload_digest,
            normalized_payload=normalized,
        )

    def _blocked(
        self, payload: Mapping[str, Any] | None, *, tenant_id: str | None,
        actor_id: str | None, service_identity: str | None, source: str,
        correlation_id: str, trigger_id: str, code: str, reason: str,
    ) -> InvestigationIntakeResult:
        safe_source = _safe_text(source or "generic", "source") or "generic"
        normalized = {}
        try:
            if tenant_id:
                normalized = self.normalize_alert(payload, tenant_id=tenant_id, source=safe_source)
        except Exception:
            normalized = {}
        source_event_id = _safe_text(
            normalized.get("source_event_id") if normalized else None,
            "source_event_id",
        ) or f"rejected:{trigger_id}"
        key = f"{safe_source}:{source_event_id}"
        digest = _digest(normalized)
        trigger = None
        if tenant_id and (actor_id or service_identity):
            try:
                trigger = self._make_trigger(
                    normalized or {"source": safe_source, "source_event_id": source_event_id},
                    tenant_id, actor_id, service_identity, correlation_id, trigger_id,
                    key, digest, "BLOCKED", "BLOCKED", reason, None,
                )
                trigger, _ = self.repository.create_trigger(trigger)
                self._audit(trigger, "intake_rejected", {"code": code, "reason": reason})
                self._audit(trigger, "investigation_intake_blocked", {"code": code, "reason": reason})
            except (ValueError, PermissionError, JobConflictError):
                trigger = None
        if trigger is None:
            self.audit_service.record(
                "investigation_intake_blocked", tenant_id=tenant_id, actor_id=actor_id,
                correlation_id=correlation_id, resource_type="investigation_intake",
                resource_id=trigger_id, operation="intake", outcome="blocked",
                details={"code": code, "reason": reason, "trigger_id": trigger_id},
            )
        return InvestigationIntakeResult(
            accepted=False, duplicate=False, status="BLOCKED", code=code, reason=reason,
            trigger_id=trigger.trigger_id if trigger else trigger_id, job_id=None,
            state=None, correlation_id=correlation_id, http_status=403 if code != "malformed_alert" else 400,
        )

    def _audit(self, trigger: InvestigationTrigger, event_type: str, metadata: dict[str, Any]) -> None:
        self.repository.record_trigger_audit_event(
            tenant_id=trigger.tenant_id, trigger_id=trigger.trigger_id, event_type=event_type,
            actor_id=trigger.actor_id, service_identity=trigger.service_identity,
            correlation_id=trigger.correlation_id, job_id=trigger.job_id,
            metadata=metadata,
        )

    def _audit_unbound_or_bound(
        self, tenant_id: str | None, trigger_id: str, actor_id: str | None,
        service_identity: str | None, correlation_id: str, event_type: str,
        metadata: dict[str, Any],
    ) -> None:
        self.repository.record_trigger_audit_event(
            tenant_id=tenant_id, trigger_id=trigger_id, event_type=event_type,
            actor_id=actor_id, service_identity=service_identity or "intake-boundary",
            correlation_id=correlation_id, metadata=metadata,
        )


__all__ = [
    "EligibilityDecision", "InvestigationIntake", "InvestigationIntakeResult",
    "InvestigationTrigger",
]
