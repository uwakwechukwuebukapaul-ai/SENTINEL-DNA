"""Fail-closed policy for the single bounded investigation follow-up."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping
from typing import Any, Callable

from services.intelligence.reasoning.evidence_sufficiency import EvidenceSufficiencyResult, SufficiencyStatus
from services.intelligence.runtime.task import Task
from services.intelligence.runtime.task_priority import TaskPriority
from services.intelligence.investigation.canonical import sha256_digest


class InvestigationPolicyViolation(ValueError):
    """A follow-up request failed a mandatory runtime guard."""


def _utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class InvestigationRuntimePolicy:
    max_iterations: int = 1
    maximum_tasks: int = 1
    maximum_duration_seconds: int = 900
    task_deadline_seconds: int = 300
    provider_call_budget: int = 1
    tenant_provider_quota: float = 1.0
    ai_token_budget: int = 0
    tenant_quota_hook: Callable[[str, float], bool] | None = None
    provider_call_budget_hook: Callable[[str, int], bool] | None = None
    ai_token_budget_hook: Callable[[str, int], bool] | None = None
    allowed_capabilities: frozenset[str] = frozenset({
        "evidence_lookup", "read_only_evidence_lookup", "read_only_context_lookup",
        "threat_intelligence_lookup",
    })
    destructive_capabilities: frozenset[str] = frozenset({
        "delete", "disable", "isolate", "quarantine", "kill", "block", "remediate", "rollback",
        "write", "modify", "execute_command", "response", "containment",
    })
    max_follow_up_budget: float = 1.0

    def __post_init__(self) -> None:
        if self.max_iterations != 1:
            raise InvestigationPolicyViolation("max_iterations must be exactly 1")
        if self.maximum_tasks != 1 or self.maximum_duration_seconds <= 0 or self.task_deadline_seconds <= 0:
            raise InvestigationPolicyViolation("bounded runtime limits are invalid")
        if self.provider_call_budget < 0 or self.ai_token_budget < 0 or self.tenant_provider_quota < 0 or self.max_follow_up_budget <= 0:
            raise InvestigationPolicyViolation("runtime budgets are invalid")

    def enforce_execution(self, *, job: Any, started_at: Any, now: Any,
                          provider_calls: int = 0, ai_tokens: int = 0) -> None:
        try:
            elapsed = (_utc(now) - _utc(started_at)).total_seconds()
            if elapsed > self.maximum_duration_seconds:
                raise InvestigationPolicyViolation("maximum investigation duration exceeded")
            if provider_calls > self.provider_call_budget or ai_tokens > self.ai_token_budget:
                raise InvestigationPolicyViolation("investigation budget exceeded")
            if self.provider_call_budget_hook and not self.provider_call_budget_hook(str(job.tenant_id), provider_calls):
                raise InvestigationPolicyViolation("provider-call budget hook denied execution")
            if self.ai_token_budget_hook and not self.ai_token_budget_hook(str(job.tenant_id), ai_tokens):
                raise InvestigationPolicyViolation("AI/token budget hook denied execution")
        except InvestigationPolicyViolation:
            raise
        except Exception as exc:
            raise InvestigationPolicyViolation("runtime policy could not be evaluated") from exc

    def authorize_provider_calls(self, *, job: Any, call_count: int, call_cost: float = 1.0) -> None:
        """Authorize a bounded provider invocation before any gateway call."""
        if int(call_count) < 1 or int(call_count) > self.provider_call_budget:
            raise InvestigationPolicyViolation("provider-call budget exhausted")
        if float(call_cost) <= 0 or float(call_cost) > float(call_count):
            raise InvestigationPolicyViolation("provider-call cost is invalid")
        if self.provider_call_budget_hook:
            try:
                if not self.provider_call_budget_hook(str(job.tenant_id), int(call_count)):
                    raise InvestigationPolicyViolation("provider-call budget hook denied execution")
            except InvestigationPolicyViolation:
                raise
            except Exception as exc:
                raise InvestigationPolicyViolation("provider-call budget hook failed closed") from exc

    def create_follow_up_task(
        self, *, job: Any, parent_task_id: str, sufficiency: EvidenceSufficiencyResult,
        cancellation_requested: bool = False, now: Any | None = None,
        known_iocs: Any = None,
    ) -> Task:
        if cancellation_requested:
            raise InvestigationPolicyViolation("cancellation requested before follow-up creation")
        if sufficiency.status != SufficiencyStatus.INSUFFICIENT:
            raise InvestigationPolicyViolation("only insufficient evidence can create follow-up work")
        if int(getattr(job, "iteration", 0)) != 0 or self.max_iterations != 1:
            raise InvestigationPolicyViolation("follow-up iteration is not permitted")
        if not all(getattr(job, field, None) for field in ("job_id", "tenant_id", "case_id", "investigation_id", "execution_id", "correlation_id")):
            raise InvestigationPolicyViolation("follow-up identity is incomplete")
        recommendation = dict(sufficiency.recommended_follow_up or {})
        capability = str(recommendation.get("capability") or "").strip()
        authorization_reference = str(recommendation.get("authorization_reference") or "").strip()
        if not capability or capability not in self.allowed_capabilities or self._destructive(capability):
            raise InvestigationPolicyViolation("follow-up capability is not explicitly allowlisted")
        if not authorization_reference:
            raise InvestigationPolicyViolation("follow-up authorization is required")
        gaps = tuple(sorted(set(str(item).strip() for item in sufficiency.evidence_gaps if str(item).strip())))
        if not gaps:
            raise InvestigationPolicyViolation("follow-up must derive from a recorded evidence gap")
        required_evidence = tuple(str(item) for item in (recommendation.get("required_evidence") or gaps))
        if not required_evidence or any(item not in gaps for item in required_evidence):
            raise InvestigationPolicyViolation("follow-up evidence lineage is invalid")
        provider_request = None
        if capability == "threat_intelligence_lookup":
            raw_request = recommendation.get("provider_request") or recommendation.get("request")
            if not isinstance(raw_request, Mapping):
                raise InvestigationPolicyViolation("provider lookup request is required")
            ioc_type = str(raw_request.get("ioc_type") or "").strip().lower()
            ioc_value = str(raw_request.get("ioc_value") or "").strip().lower()
            if ioc_type not in {"ip", "domain", "url", "hash", "email", "unknown"} or not ioc_value or len(ioc_value) > 2048:
                raise InvestigationPolicyViolation("provider lookup request is invalid")
            if known_iocs is not None:
                known = {
                    (str(item.get("type", "unknown")).lower(), str(item.get("value", "")).strip().lower())
                    for item in (known_iocs or ()) if isinstance(item, Mapping)
                }
                if (ioc_type, ioc_value) not in known:
                    raise InvestigationPolicyViolation("provider lookup IOC is not present in the trusted snapshot")
            provider_request = {"ioc_type": ioc_type, "ioc_value": ioc_value}
        cost = float(recommendation.get("budget_cost", 1.0))
        if cost <= 0 or cost > self.max_follow_up_budget:
            raise InvestigationPolicyViolation("follow-up budget is unavailable")
        if self.tenant_quota_hook:
            try:
                if not self.tenant_quota_hook(str(job.tenant_id), cost):
                    raise InvestigationPolicyViolation("tenant quota hook denied follow-up")
            except InvestigationPolicyViolation:
                raise
            except Exception as exc:
                raise InvestigationPolicyViolation("tenant quota hook failed closed") from exc
        timestamp = _utc(now or datetime.now(timezone.utc))
        identity = {
            "job_id": str(job.job_id), "parent_task_id": str(parent_task_id), "tenant_id": str(job.tenant_id),
            "case_id": str(job.case_id), "investigation_id": str(job.investigation_id),
            "execution_id": str(job.execution_id), "capability": capability,
            "gaps": gaps, "required_evidence": required_evidence, "authorization_reference": authorization_reference,
            "iteration": 1,
            "provider_request": provider_request,
        }
        digest = sha256_digest(identity)
        objective = f"Collect recorded evidence gap: {gaps[0]}"
        return Task(
            task_id=f"FU-{digest[:24]}", execution_id=str(job.execution_id), capability=capability,
            payload={
                "case_id": str(job.case_id), "tenant_id": str(job.tenant_id),
                "investigation_id": str(job.investigation_id), "job_id": str(job.job_id),
                "correlation_id": str(job.correlation_id), "objective": objective,
                "required_evidence": list(required_evidence), "authorization_reference": authorization_reference,
                "evidence_gap_digest": sha256_digest(gaps), "iteration": 1,
                **({"provider_request": provider_request} if provider_request else {}),
            },
            priority=TaskPriority.NORMAL, parent_task_id=str(parent_task_id), job_id=str(job.job_id),
            tenant_id=str(job.tenant_id), case_id=str(job.case_id), investigation_id=str(job.investigation_id),
            objective=objective, required_evidence=list(required_evidence), iteration=1,
            authorization_reference=authorization_reference, budget_cost=cost, created_at=timestamp,
            available_at=timestamp, deadline_at=timestamp + timedelta(seconds=self.task_deadline_seconds),
            metadata={"provenance": "bounded_evidence_gap", "sufficiency_digest": sufficiency.input_evidence_digest,
                      **({"provider_request": provider_request} if provider_request else {})},
        )

    def _destructive(self, capability: str) -> bool:
        normalized = capability.lower().replace("-", "_")
        return any(term in normalized for term in self.destructive_capabilities)


__all__ = ["InvestigationPolicyViolation", "InvestigationRuntimePolicy"]
