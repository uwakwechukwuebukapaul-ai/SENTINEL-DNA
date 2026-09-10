"""Append-only, tenant-scoped investigation performance telemetry.

Telemetry is observational only. It never authorizes work, changes a verdict,
or raises an error into the investigation path when persistence is unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import hashlib
import json
import time
from typing import Any, Callable
from uuid import uuid4

from services.audit.service import AuditService


COMPONENTS = (
    "coordinator",
    "orchestrator",
    "evidence_retrieval",
    "ioc_enrichment",
    "mitre_mapping",
    "memory_retrieval",
    "reasoning",
    "report_generation",
)


@dataclass
class _OpenStage:
    component: str
    started_at: float


class InvestigationPerformanceTrace:
    """One investigation trace with monotonic component measurements."""

    def __init__(
        self,
        *,
        audit_service: AuditService | None,
        case_id: str,
        tenant_id: str | None,
        investigation_id: str | None = None,
        execution_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.audit_service = audit_service
        self.trace_id = str(uuid4())
        self.case_id = str(case_id)
        self.tenant_id = str(tenant_id) if tenant_id else None
        self.investigation_id = str(investigation_id) if investigation_id else None
        self.execution_id = str(execution_id) if execution_id else None
        self.correlation_id = str(correlation_id) if correlation_id else None
        self.started_at = time.perf_counter()
        self._open: list[_OpenStage] = []
        self._durations: dict[str, list[float]] = {component: [] for component in COMPONENTS}
        self._statuses: dict[str, list[str]] = {component: [] for component in COMPONENTS}
        self._finished = False
        self.summary: dict[str, Any] | None = None

    def begin_stage(self, component: str) -> None:
        name = str(component)
        if name not in COMPONENTS:
            raise ValueError(f"unknown_investigation_telemetry_component:{name}")
        self._open.append(_OpenStage(name, time.perf_counter()))

    def end_stage(self, component: str, *, status: str = "completed") -> float:
        name = str(component)
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index].component == name:
                stage = self._open.pop(index)
                duration = round(max(0.0, time.perf_counter() - stage.started_at) * 1000, 6)
                self._durations[name].append(duration)
                self._statuses[name].append(str(status))
                return duration
        return 0.0

    def _close_open_stages(self, *, status: str) -> None:
        while self._open:
            self.end_stage(self._open[-1].component, status=status)

    def _summary(self, *, status: str, error_type: str | None = None) -> dict[str, Any]:
        end_to_end = round(max(0.0, time.perf_counter() - self.started_at) * 1000, 6)
        components = {
            name: {
                "duration_ms": round(sum(self._durations[name]), 6),
                "span_count": len(self._durations[name]),
                "statuses": list(self._statuses[name]),
            }
            for name in COMPONENTS
        }
        # The coordinator span is the end-to-end envelope. It intentionally
        # overlaps child components so investigators can compare total cost
        # with internal attribution; component totals are not additive.
        components["coordinator"] = {
            "duration_ms": end_to_end,
            "span_count": 1,
            "statuses": [str(status)],
            "is_end_to_end_envelope": True,
        }
        summary: dict[str, Any] = {
            "telemetry_version": "investigation-performance-v1",
            "trace_id": self.trace_id,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "tenant_id": self.tenant_id,
            "status": str(status),
            "end_to_end_latency_ms": end_to_end,
            "components": components,
            "component_order": list(COMPONENTS),
            "append_only_audit": True,
            "tenant_scoped": bool(self.tenant_id),
            "authorization_impact": "none",
            "decision_impact": "none",
            "fail_closed_impact": "none",
            "provenance": {
                "source": "InvestigationCoordinator",
                "measurement_clock": "monotonic",
                "case_id": self.case_id,
                "tenant_id": self.tenant_id,
            },
        }
        if error_type:
            summary["error_type"] = str(error_type)
        return summary

    def finish(
        self,
        *,
        status: str = "completed",
        result: Any = None,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        if self._finished and self.summary is not None:
            return self.summary
        self._close_open_stages(status="failed" if str(status).lower() == "failed" else "completed")
        summary = self._summary(status=status, error_type=error_type)
        if self.tenant_id and self.audit_service is not None:
            try:
                audit_id = self.audit_service.record(
                    "investigation_performance_telemetry",
                    case_id=self.case_id,
                    details=summary,
                    tenant_id=self.tenant_id,
                    actor_id=None,
                    correlation_id=self.correlation_id,
                    resource_type="investigation",
                    resource_id=self.investigation_id or self.case_id,
                    operation="observe_performance",
                    outcome=str(status),
                    latency_ms=summary["end_to_end_latency_ms"],
                )
                summary["audit_event_id"] = audit_id
                summary["audit_status"] = "persisted"
            except Exception as exc:
                summary["audit_status"] = "persistence_failed"
                summary["audit_error_type"] = type(exc).__name__
        else:
            summary["audit_status"] = "not_persisted_tenant_required"
        summary["evidence_digest"] = hashlib.sha256(
            json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        self._finished = True
        self.summary = summary
        if result is not None and hasattr(result, "metadata") and isinstance(result.metadata, dict):
            result.metadata["performance_telemetry"] = summary
        return summary


class InvestigationPerformanceTelemetry:
    """Factory for traces sharing one append-only audit boundary."""

    def __init__(self, audit_service: AuditService | None = None) -> None:
        self.audit_service = audit_service

    def start_trace(
        self,
        *,
        case_id: str,
        tenant_id: str | None,
        investigation_id: str | None = None,
        execution_id: str | None = None,
        correlation_id: str | None = None,
    ) -> InvestigationPerformanceTrace:
        return InvestigationPerformanceTrace(
            audit_service=self.audit_service,
            case_id=case_id,
            tenant_id=tenant_id,
            investigation_id=investigation_id,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )


def instrument_investigation(method: Callable[..., Any]) -> Callable[..., Any]:
    """Decorate a coordinator method without changing its public contract."""

    @wraps(method)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        case_id = kwargs.get("case_id") or (args[0] if args else "unknown")
        tenant_id = kwargs.get("tenant_id")
        correlation_id = kwargs.get("correlation_id")
        telemetry = self.performance_telemetry.start_trace(
            case_id=str(case_id),
            tenant_id=str(tenant_id) if tenant_id else None,
            investigation_id=(kwargs.get("investigation_id") or None),
            execution_id=(kwargs.get("execution_id") or None),
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        call_kwargs = dict(kwargs)
        call_kwargs["_performance_telemetry"] = telemetry
        try:
            result = method(self, *args, **call_kwargs)
        except Exception as exc:
            telemetry.finish(status="failed", error_type=type(exc).__name__)
            raise
        telemetry.investigation_id = str(getattr(result, "investigation_id", None) or case_id)
        telemetry.execution_id = str(getattr(result, "execution_id", None) or telemetry.execution_id or "") or None
        telemetry.finish(status=str(getattr(result, "status", "completed")), result=result)
        return result

    return wrapped


__all__ = [
    "COMPONENTS",
    "InvestigationPerformanceTelemetry",
    "InvestigationPerformanceTrace",
    "instrument_investigation",
]
