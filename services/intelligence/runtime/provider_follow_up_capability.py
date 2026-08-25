"""One bounded, read-only provider-observation-backed follow-up capability.

The capability is intentionally narrow: it adapts the existing provider-neutral
threat-intelligence gateway into the P0.5 Task boundary, persists only the
normalized ProviderObservation contract, and never refreshes an existing
deterministic request during replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Callable, Mapping
from typing import Any

from app.intelligence.gateway import IOC, IOCType, LookupRequest
from services.intelligence.investigation.canonical import sha256_digest
from services.intelligence.investigation.provider_observation import ProviderObservation
from services.intelligence.repository.execution_repository import (
    ExecutionRepository,
    ProviderBudgetError,
    ProviderObservationLineageError,
)
from services.intelligence.repository.provider_observation_repository import ProviderObservationRepository
from services.intelligence.runtime.investigation_runtime_policy import (
    InvestigationPolicyViolation,
    InvestigationRuntimePolicy,
)
from services.intelligence.runtime.task import Task


CAPABILITY_THREAT_INTELLIGENCE_LOOKUP = "threat_intelligence_lookup"


class ProviderFollowUpError(RuntimeError):
    """A provider follow-up failed at a controlled, auditable boundary."""

    def __init__(self, code: str, message: str, *, terminal_state: str = "BLOCKED") -> None:
        super().__init__(message)
        self.code = str(code)
        self.terminal_state = str(terminal_state).upper()


@dataclass(frozen=True)
class ProviderFollowUpResult:
    success: bool
    status: str
    evidence: tuple[Mapping[str, Any], ...] = ()
    observation_ids: tuple[str, ...] = ()
    provider_health: tuple[Mapping[str, Any], ...] = ()
    error_code: str | None = None
    replay_reused: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "evidence": [dict(item) for item in self.evidence],
            "provider_observation_references": list(self.observation_ids),
            "metadata": {
                "provider_follow_up": True,
                "provider_health": [dict(item) for item in self.provider_health],
                "error_code": self.error_code,
                "replay_reused": self.replay_reused,
                "evidence_sufficiency": "SUFFICIENT" if self.evidence else "UNKNOWN",
            },
        }


class ReadOnlyFollowUpCapabilityRegistry:
    """Explicit registry; capability names cannot be invented at runtime."""

    ALLOWLIST = frozenset({CAPABILITY_THREAT_INTELLIGENCE_LOOKUP})

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}

    def register(self, capability: str, handler: Any) -> None:
        name = str(capability or "").strip()
        if name not in self.ALLOWLIST or not callable(getattr(handler, "execute_follow_up", None)):
            raise ValueError("read-only follow-up capability is not explicitly registered")
        self._handlers[name] = handler

    def resolve(self, capability: str) -> Any:
        name = str(capability or "").strip()
        if name not in self.ALLOWLIST or name not in self._handlers:
            raise ProviderFollowUpError("capability_blocked", "follow-up capability is not registered")
        return self._handlers[name]


class ProviderObservationFollowUpExecutor:
    """Execute one authorized threat-intelligence lookup through the gateway."""

    capability = CAPABILITY_THREAT_INTELLIGENCE_LOOKUP

    def __init__(
        self,
        gateway: Any,
        observation_repository: ProviderObservationRepository,
        execution_repository: ExecutionRepository,
        *,
        authorization_context_factory: Callable[[Any], Any],
        provider_authorizer: Callable[[str, str, str], bool],
        runtime_policy: InvestigationRuntimePolicy,
        approved_provider: str | None = None,
        release_gate: Callable[[str, str, str, str], bool] | None = None,
        service_authorizer: Callable[[str, str, str], bool] | None = None,
        capability_registry: ReadOnlyFollowUpCapabilityRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
        service_identity: str | None = None,
    ) -> None:
        if not callable(getattr(gateway, "lookup", None)):
            raise TypeError("provider-neutral gateway is required")
        if not isinstance(observation_repository, ProviderObservationRepository):
            raise TypeError("provider observation repository is required")
        if not isinstance(execution_repository, ExecutionRepository):
            raise TypeError("execution repository is required")
        if not callable(authorization_context_factory) or not callable(provider_authorizer):
            raise TypeError("provider authorization boundaries are required")
        if not isinstance(runtime_policy, InvestigationRuntimePolicy):
            raise TypeError("bounded runtime policy is required")
        self.gateway = gateway
        self.observation_repository = observation_repository
        self.execution_repository = execution_repository
        self.authorization_context_factory = authorization_context_factory
        self.provider_authorizer = provider_authorizer
        self.runtime_policy = runtime_policy
        self.approved_provider = str(approved_provider or "").strip()
        self.release_gate = release_gate or (lambda *_: False)
        self.service_authorizer = service_authorizer or (lambda *_: False)
        self.capability_registry = capability_registry or ReadOnlyFollowUpCapabilityRegistry()
        self.capability_registry.register(self.capability, self)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.service_identity = str(service_identity or "").strip()
        if not self.service_identity:
            raise ValueError("provider service identity is required")

    def execute_follow_up(self, job: Any, task: Task, parent_snapshot: Any | None = None) -> dict[str, Any]:
        self._validate_identity(job, task)
        try:
            if self.capability_registry.resolve(task.capability) is not self:
                raise ProviderFollowUpError("capability_blocked", "task capability handler is not bound")
        except ProviderFollowUpError as exc:
            self._audit(job, task, "PROVIDER_CAPABILITY_DENIED", {"capability": task.capability, "reason": exc.code})
            raise
        now = self._now()
        if task.deadline_at is not None and now >= task.deadline_at.astimezone(timezone.utc):
            raise ProviderFollowUpError("task_timeout", "follow-up task deadline exceeded", terminal_state="TIMED_OUT")
        if bool(getattr(job, "cancel_requested", False)):
            raise ProviderFollowUpError("cancellation", "follow-up was cancelled", terminal_state="CANCELLED")
        context = self._authorization_context(job)
        if not self.service_authorizer(job.tenant_id, self._actor(job), self.service_identity):
            self._audit(job, task, "SERVICE_AUTHORIZATION_DENIED", {"service_identity": self.service_identity})
            self._record_denied_health(job, task, "service_unauthorized")
            raise ProviderFollowUpError("service_unauthorized", "provider service identity is not authorized")
        request_data = self._request_data(task)
        try:
            provider_names = self._authorized_provider_names(job, request_data["ioc_type"])
        except ProviderFollowUpError as exc:
            if exc.code == "provider_release_gate_denied":
                event = "PROVIDER_RELEASE_GATE_DENIED"
            elif "authoriz" in exc.code:
                event = "PROVIDER_AUTHORIZATION_DENIED"
            else:
                event = "PROVIDER_CAPABILITY_DENIED"
            self._audit(job, task, event, {"capability": task.capability, "reason": exc.code})
            self._record_denied_health(job, task, exc.code)
            raise
        request_digest = sha256_digest({
            "tenant_id": job.tenant_id, "job_id": job.job_id, "investigation_id": job.investigation_id,
            "task_id": task.task_id, "iteration": task.iteration, "capability": task.capability,
            "provider_names": provider_names, "request": request_data,
        })
        request_id = f"PVR-{request_digest[:24]}"
        request, created = self.execution_repository.reserve_provider_request({
            "request_id": request_id, "request_digest": request_digest, "job_id": job.job_id,
            "execution_id": job.execution_id, "task_id": task.task_id, "tenant_id": job.tenant_id,
            "case_id": job.case_id, "investigation_id": job.investigation_id,
            "correlation_id": job.correlation_id, "capability": task.capability, "iteration": 1,
            "service_identity": self.service_identity,
            "request": {"ioc_type": request_data["ioc_type"], "ioc_value": request_data["ioc_value"],
                         "provider_names": list(provider_names)}, "created_at": now.isoformat(),
        })
        if not created:
            return self._replay_or_fail(job, context, request)
        try:
            self.runtime_policy.authorize_provider_calls(
                job=job, call_count=len(provider_names), call_cost=float(len(provider_names)),
            )
        except InvestigationPolicyViolation as exc:
            self.execution_repository.complete_provider_request(
                request_id, job.tenant_id, status="FAILED", error_code="budget_exhausted",
                service_identity=self.service_identity,
            )
            self._audit(job, task, "PROVIDER_BUDGET_DENIED", {
                "request_id": request_id, "reason": "budget_exhausted",
            })
            self._record_denied_health(job, task, "budget_exhausted", request_id=request_id)
            raise ProviderFollowUpError("budget_exhausted", "provider-call budget exhausted") from exc
        try:
            self.execution_repository.reserve_provider_budget(
                request_id=request_id, tenant_id=job.tenant_id, job_id=job.job_id,
                investigation_id=job.investigation_id, execution_id=job.execution_id,
                task_id=task.task_id, iteration=1, request_digest=request_digest,
                provider_names=provider_names,
                tenant_quota=self.runtime_policy.tenant_provider_quota,
                now=now.isoformat(),
                service_identity=self.service_identity,
            )
        except ProviderBudgetError as exc:
            self.execution_repository.complete_provider_request(
                request_id, job.tenant_id, status="FAILED", error_code="quota_exhausted",
                service_identity=self.service_identity,
            )
            self._audit(job, task, "PROVIDER_QUOTA_DENIED", {
                "request_id": request_id, "reason": "quota_exhausted",
            })
            self._record_denied_health(job, task, "quota_exhausted", request_id=request_id)
            raise ProviderFollowUpError("quota_exhausted", "tenant provider quota exhausted") from exc
        self._audit(job, task, "PROVIDER_CAPABILITY_SELECTED", {"capability": task.capability, "request_id": request_id})
        self._audit(job, task, "PROVIDER_AUTHORIZATION_GRANTED", {"provider_count": len(provider_names), "providers": list(provider_names)})
        self._audit(job, task, "PROVIDER_QUOTA_APPROVED", {
            "request_id": request_id, "provider_count": len(provider_names),
            "reserved_cost": float(len(provider_names)),
        })
        self._audit(job, task, "PROVIDER_BUDGET_APPROVED", {"request_id": request_id, "provider_count": len(provider_names)})
        try:
            self._check_deadline(task)
            self._check_cancelled(job)
        except ProviderFollowUpError as exc:
            self._complete_request_failed(request_id, job, exc.code)
            self._finalize_budget(request_id, job, "FAILED", exc.code)
            raise
        request_object = LookupRequest(
            tenant_id=job.tenant_id, actor_id=self._actor(job),
            ioc=IOC(request_data["ioc_value"], IOCType(request_data["ioc_type"])),
            timeout_seconds=min(30.0, max(0.1, self._remaining_seconds(task))),
            correlation_id=job.correlation_id, case_id=job.case_id,
        )
        self._audit(job, task, "PROVIDER_INVOCATION_STARTED", {"request_id": request_id, "request_digest": request_digest})
        try:
            gateway_result = self.gateway.lookup(request_object)
        except PermissionError as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="unauthorized", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "unauthorized")
            self._audit(job, task, "PROVIDER_AUTHORIZATION_DENIED", {"request_id": request_id})
            raise ProviderFollowUpError("unauthorized", "provider authorization denied") from exc
        except TimeoutError as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="provider_timeout", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "provider_timeout")
            raise ProviderFollowUpError("provider_timeout", "provider lookup timed out", terminal_state="ESCALATED") from exc
        except Exception as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="provider_error", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "provider_error")
            self._audit(job, task, "PROVIDER_INVOCATION_FAILED", {"request_id": request_id, "reason": "provider_error"})
            raise ProviderFollowUpError("provider_error", "provider lookup failed", terminal_state="ESCALATED") from exc
        self._audit(job, task, "PROVIDER_INVOCATION_COMPLETED", {"request_id": request_id, "provider_count": len(gateway_result.provider_results)})
        try:
            self._check_deadline(task)
            self._check_cancelled(job)
        except ProviderFollowUpError as exc:
            self._complete_request_failed(request_id, job, exc.code)
            self._finalize_budget(request_id, job, "FAILED", exc.code)
            raise
        provider_health = [item.to_dict() for item in gateway_result.provider_health]
        self.execution_repository.save_provider_health(
            execution_id=job.execution_id, tenant_id=job.tenant_id, snapshots=provider_health,
            request_id=request_id, job_id=job.job_id, task_id=task.task_id,
            investigation_id=job.investigation_id, iteration=1,
            correlation_id=job.correlation_id,
            outcome=self._gateway_error_code(gateway_result) or ("success" if gateway_result.successful else "provider_failure"),
        )
        observations: list[ProviderObservation] = []
        try:
            for provider_result in gateway_result.provider_results:
                observation = ProviderObservation.from_provider_result(
                    provider_result, audit=gateway_result.audit, tenant_id=job.tenant_id,
                    case_id=job.case_id, actor_id=self._actor(job), correlation_id=job.correlation_id,
                )
                self.observation_repository.save_for_tenant(
                    job.tenant_id, observation, authorization_context=context,
                )
                observations.append(observation)
                self._audit(job, task, "PROVIDER_OBSERVATION_PERSISTED", {
                    "request_id": request_id, "observation_id": observation.observation_id,
                    "observation_digest": observation.integrity_digest, "provider": observation.provider_name,
                })
        except PermissionError as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="unauthorized", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "unauthorized")
            raise ProviderFollowUpError("unauthorized", "provider observation authorization denied") from exc
        except Exception as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="replay_integrity_failure", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "replay_integrity_failure")
            raise ProviderFollowUpError("replay_integrity_failure", "provider observation failed integrity validation") from exc
        try:
            self.execution_repository.link_provider_observations(
                request_id=request_id, tenant_id=job.tenant_id,
                observation_ids=[item.observation_id for item in observations],
                authorization_reference=task.authorization_reference or "",
                capability=task.capability,
                service_identity=self.service_identity,
            )
        except ProviderObservationLineageError as exc:
            self.execution_repository.complete_provider_request(request_id, job.tenant_id, status="FAILED", error_code="replay_integrity_failure", service_identity=self.service_identity)
            self._finalize_budget(request_id, job, "FAILED", "replay_integrity_failure")
            raise ProviderFollowUpError("replay_integrity_failure", "provider observation lineage failed") from exc
        try:
            self._check_cancelled(job)
        except ProviderFollowUpError as exc:
            self._complete_request_failed(request_id, job, exc.code)
            self._finalize_budget(request_id, job, "FAILED", exc.code)
            raise
        observation_ids = tuple(item.observation_id for item in observations)
        error_code = self._gateway_error_code(gateway_result)
        self.execution_repository.complete_provider_request(
            request_id, job.tenant_id, status="COMPLETED", observation_ids=observation_ids,
            error_code=error_code, service_identity=self.service_identity,
        )
        self._finalize_budget(request_id, job, "CONSUMED", error_code or "success")
        evidence = tuple(item.to_evidence() for item in observations if item.status in {"success", "partial", "stale"})
        self._audit(job, task, "PROVIDER_EVIDENCE_PROJECTED", {
            "request_id": request_id, "observation_count": len(observations), "evidence_count": len(evidence),
            "observation_ids": list(observation_ids),
        })
        return ProviderFollowUpResult(
            success=True, status="completed", evidence=evidence, observation_ids=observation_ids,
            provider_health=tuple(provider_health),
            error_code=error_code,
        ).to_dict()

    def _replay_or_fail(self, job: Any, context: Any, request: Mapping[str, Any]) -> dict[str, Any]:
        status = str(request.get("status") or "")
        if status == "IN_FLIGHT":
            raise ProviderFollowUpError("duplicate_request_in_flight", "provider request is already in flight")
        if str(request.get("error_code") or "") == "quota_exhausted":
            raise ProviderFollowUpError("quota_exhausted", "tenant provider quota exhausted")
        observation_ids = tuple(str(item) for item in request.get("observation_ids") or ())
        if not observation_ids:
            return ProviderFollowUpResult(
                success=True, status="completed", error_code=request.get("error_code") or "provider_unavailable",
            ).to_dict()
        try:
            self.execution_repository.verify_provider_observation_links(
                request_id=str(request["request_id"]), tenant_id=job.tenant_id,
                job_id=job.job_id, investigation_id=job.investigation_id,
                execution_id=job.execution_id, task_id=str(request["task_id"]),
                observation_ids=observation_ids,
            )
            observations = self.observation_repository.resolve_for_replay(
                observation_ids, tenant_id=job.tenant_id, case_id=job.case_id,
                correlation_id=job.correlation_id, actor_id=self._actor(job), authorization_context=context,
            )
        except Exception as exc:
            self._audit(job, self._task_from_request(request), "PROVIDER_REPLAY_REJECTED", {"request_id": request["request_id"]})
            raise ProviderFollowUpError("replay_integrity_failure", "stored provider observation replay failed") from exc
        self._audit(job, self._task_from_request(request), "PROVIDER_REPLAY_REUSED", {
            "request_id": request["request_id"], "observation_count": len(observations),
        })
        evidence = tuple(item.to_evidence() for item in observations if item.status in {"success", "partial", "stale"})
        return ProviderFollowUpResult(
            success=True, status="completed", evidence=evidence, observation_ids=observation_ids,
            error_code=request.get("error_code"), replay_reused=True,
        ).to_dict()

    def _authorized_provider_names(self, job: Any, ioc_type: str) -> tuple[str, ...]:
        if not self.approved_provider:
            raise ProviderFollowUpError("provider_release_gate_denied", "no provider is explicitly release-approved")
        providers = tuple(getattr(self.gateway, "_providers", ()) or ())
        candidates = [provider for provider in providers if str(provider.identity.name) == self.approved_provider and IOCType(ioc_type) in provider.capabilities()]
        if not candidates:
            raise ProviderFollowUpError("provider_release_gate_denied", "approved provider is unavailable")
        names = tuple(sorted(str(provider.identity.name) for provider in candidates))
        if any(not self.provider_authorizer(job.tenant_id, self._actor(job), name) for name in names):
            raise ProviderFollowUpError("provider_unauthorized", "provider authorization denied")
        if any(not self.release_gate(job.tenant_id, self._actor(job), self.service_identity, name) for name in names):
            raise ProviderFollowUpError("provider_release_gate_denied", "provider release gate denied execution")
        return names

    def _authorization_context(self, job: Any) -> Any:
        context = self.authorization_context_factory(job)
        if not context:
            raise ProviderFollowUpError("unauthorized", "provider authorization context is missing")
        if str(getattr(context, "tenant_id", "")) != str(job.tenant_id) or str(getattr(context, "actor_id", "")) != self._actor(job):
            raise ProviderFollowUpError("tenant_mismatch", "provider authorization context does not match job")
        if getattr(context, "correlation_id", None) not in (None, job.correlation_id):
            raise ProviderFollowUpError("tenant_mismatch", "provider authorization correlation does not match job")
        return context

    @staticmethod
    def _validate_identity(job: Any, task: Task) -> None:
        if task.iteration != 1 or any(getattr(task, field, None) != getattr(job, field, None) for field in ("job_id", "tenant_id", "case_id", "investigation_id")):
            raise ProviderFollowUpError("tenant_mismatch", "provider task lineage does not match job")
        if not task.authorization_reference:
            raise ProviderFollowUpError("unauthorized", "provider task authorization is missing")

    @staticmethod
    def _request_data(task: Task) -> dict[str, str]:
        value = task.payload.get("provider_request") if isinstance(task.payload, Mapping) else None
        if not isinstance(value, Mapping):
            raise ProviderFollowUpError("capability_blocked", "provider request parameters are missing")
        ioc_type = str(value.get("ioc_type") or "").lower()
        ioc_value = str(value.get("ioc_value") or "").strip().lower()
        try:
            IOCType(ioc_type)
        except ValueError as exc:
            raise ProviderFollowUpError("capability_blocked", "provider request IOC type is invalid") from exc
        if not ioc_value or len(ioc_value) > 2048:
            raise ProviderFollowUpError("capability_blocked", "provider request IOC value is invalid")
        return {"ioc_type": ioc_type, "ioc_value": ioc_value}

    def _check_cancelled(self, job: Any) -> None:
        if bool(getattr(job, "cancel_requested", False)) or self.execution_repository.get_cancellation_state(job.job_id, job.tenant_id):
            raise ProviderFollowUpError("cancellation", "provider follow-up was cancelled", terminal_state="CANCELLED")

    def _check_deadline(self, task: Task) -> None:
        if task.deadline_at is not None and self._now() >= task.deadline_at.astimezone(timezone.utc):
            raise ProviderFollowUpError("task_timeout", "follow-up task deadline exceeded", terminal_state="TIMED_OUT")

    def _complete_request_failed(self, request_id: str, job: Any, error_code: str) -> None:
        self.execution_repository.complete_provider_request(
            request_id, job.tenant_id, status="FAILED", error_code=error_code,
            service_identity=self.service_identity,
        )

    def _finalize_budget(self, request_id: str, job: Any, status: str, outcome: str) -> None:
        self.execution_repository.finalize_provider_budget(
            request_id=request_id, tenant_id=job.tenant_id, status=status,
            outcome=outcome, service_identity=self.service_identity,
        )

    def _record_denied_health(
        self, job: Any, task: Task, reason: str, *, request_id: str | None = None,
    ) -> None:
        self.execution_repository.save_provider_health(
            execution_id=job.execution_id, tenant_id=job.tenant_id,
            snapshots=[{
                "provider": self.approved_provider or "unapproved",
                "status": "UNAVAILABLE", "timestamp": self._now().isoformat(),
                "failure_count": 1, "policy_decision": "denied",
                "unavailable_reason": str(reason)[:128],
            }],
            request_id=request_id, job_id=job.job_id, task_id=task.task_id,
            investigation_id=job.investigation_id, iteration=task.iteration,
            correlation_id=job.correlation_id, outcome=str(reason)[:128],
        )

    def _remaining_seconds(self, task: Task) -> float:
        if task.deadline_at is None:
            return 30.0
        return max(0.1, (task.deadline_at.astimezone(timezone.utc) - self._now()).total_seconds())

    def _now(self) -> datetime:
        value = self.clock()
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _actor(job: Any) -> str:
        return str(getattr(job, "actor_id", None) or getattr(job, "service_identity", None) or "")

    @staticmethod
    def _gateway_error_code(result: Any) -> str | None:
        errors = [item.error for item in result.provider_results if getattr(item, "error", None) is not None]
        if not errors:
            return None
        code = getattr(errors[0], "code", None)
        return f"provider_{getattr(code, 'value', str(code))}"

    def _audit(self, job: Any, task: Task, event_type: str, metadata: Mapping[str, Any]) -> None:
        self.execution_repository.record_audit_event(
            tenant_id=job.tenant_id, job_id=job.job_id, event_type=event_type,
            actor_id=getattr(job, "actor_id", None), service_identity=self.service_identity,
            correlation_id=job.correlation_id, case_id=job.case_id,
            investigation_id=job.investigation_id, execution_id=job.execution_id,
            task_id=task.task_id, metadata=dict(metadata),
        )

    @staticmethod
    def _task_from_request(request: Mapping[str, Any]) -> Task:
        return Task(
            task_id=str(request["task_id"]), capability=str(request["capability"]), payload=dict(request.get("request") or {}),
            job_id=str(request["job_id"]), tenant_id=str(request["tenant_id"]), case_id=str(request["case_id"]),
            investigation_id=str(request["investigation_id"]), iteration=1,
            authorization_reference="replay", objective="replay stored provider observation",
        )


__all__ = [
    "CAPABILITY_THREAT_INTELLIGENCE_LOOKUP", "ProviderFollowUpError", "ProviderFollowUpResult",
    "ReadOnlyFollowUpCapabilityRegistry", "ProviderObservationFollowUpExecutor",
]
