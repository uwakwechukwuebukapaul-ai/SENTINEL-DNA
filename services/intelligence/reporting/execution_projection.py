"""Versioned analyst projection for persisted investigation execution state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping


PROJECTION_VERSION = "execution-projection-v1"


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _duration(started_at: str | None, completed_at: str | None) -> float | None:
    if not started_at or not completed_at:
        return None
    try:
        return round((datetime.fromisoformat(completed_at.replace("Z", "+00:00")) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds(), 3)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ExecutionProjectionV1:
    version: str
    execution_id: str
    tenant_id: str
    case_id: str
    alert_reference: str
    status: str
    started_at: str | None
    completed_at: str | None
    duration: float | None
    tasks: list[dict[str, Any]]
    providers: list[dict[str, Any]]
    evidence_refs: list[str]
    reasoning_summary: dict[str, Any]
    decision_summary: dict[str, Any]
    confidence: Any
    provenance: dict[str, Any]
    failures: list[dict[str, Any]]
    unavailable_reasons: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionProjectionBuilder:
    """Compose operational state with existing tenant-scoped intelligence."""

    def build(
        self,
        envelope: Mapping[str, Any],
        *,
        providers: list[Mapping[str, Any]] | None = None,
        report: Mapping[str, Any] | None = None,
        intelligence: Mapping[str, Any] | None = None,
    ) -> ExecutionProjectionV1:
        report_data = _dict(report)
        intelligence_data = _dict(intelligence)
        reasoning = report_data.get("reasoning") or report_data.get("reasoning_report") or intelligence_data.get("reasoning") or {}
        decision = report_data.get("decision_report") or report_data.get("decision") or intelligence_data.get("decision_report") or {}
        confidence = report_data.get("confidence", intelligence_data.get("confidence"))
        provider_rows = [dict(item) for item in (providers or envelope.get("provider_states", []) or [])]
        provider_rows = [
            {
                "provider": item.get("provider") or item.get("provider_name") or "Unavailable",
                "status": item.get("status") or item.get("health_status") or item.get("availability_state") or "UNAVAILABLE",
                "availability_state": item.get("availability_state") or item.get("status") or "UNAVAILABLE",
                "latency_ms": item.get("latency_ms"),
                "checked_at": item.get("checked_at") or item.get("timestamp"),
                "policy_decision": item.get("policy_decision") or "Unavailable",
                "failure_count": item.get("failure_count", 0),
                "unavailable_reason": item.get("unavailable_reason"),
            }
            for item in provider_rows
        ]
        return ExecutionProjectionV1(
            version=PROJECTION_VERSION,
            execution_id=str(envelope.get("execution_id") or "unknown"),
            tenant_id=str(envelope.get("tenant_id") or ""),
            case_id=str(envelope.get("investigation_id") or "unknown"),
            alert_reference=str(envelope.get("alert_reference") or "unknown"),
            status=str(envelope.get("status") or "UNAVAILABLE"),
            started_at=envelope.get("started_at"),
            completed_at=envelope.get("completed_at"),
            duration=_duration(envelope.get("started_at"), envelope.get("completed_at")),
            tasks=list(envelope.get("task_states", []) or []),
            providers=provider_rows,
            evidence_refs=[str(value) for value in envelope.get("evidence_references", []) or []],
            reasoning_summary=reasoning if isinstance(reasoning, dict) else {"summary": str(reasoning)},
            decision_summary=decision if isinstance(decision, dict) else {"summary": str(decision)},
            confidence=confidence if confidence is not None else "Unavailable",
            provenance={
                "source": "execution_repository",
                "version": PROJECTION_VERSION,
                "tenant_id": envelope.get("tenant_id"),
                "investigation_id": envelope.get("investigation_id"),
            },
            failures=list(envelope.get("failures", []) or []),
            unavailable_reasons=list(envelope.get("unavailable_reasons", []) or []),
        )


__all__ = ["ExecutionProjectionV1", "ExecutionProjectionBuilder", "PROJECTION_VERSION"]
