"""Application persistence boundary for completed investigations."""

from __future__ import annotations

from typing import Any

from .investigation_repository import InvestigationRepository


class InvestigationPersistenceService:
    def __init__(self, investigation_repository: InvestigationRepository | None = None) -> None:
        self.investigations = investigation_repository or InvestigationRepository()

    def start(self, investigation_id: str, case_id: str, *, tenant_id: str | None = None, actor_id: str | None = None, correlation_id: str | None = None) -> dict[str, Any]:
        self.investigations.save_lifecycle(
            investigation_id=investigation_id, case_id=case_id, tenant_id=tenant_id,
            actor_id=actor_id, correlation_id=correlation_id, status="created",
        )
        return self.investigations.save_lifecycle(
            investigation_id=investigation_id, case_id=case_id, tenant_id=tenant_id,
            actor_id=actor_id, correlation_id=correlation_id, status="running",
        )

    def persist_result(self, result: Any, *, tenant_id: str | None = None, actor_id: str | None = None, correlation_id: str | None = None) -> dict[str, Any]:
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        investigation_id = str(payload.get("investigation_id") or payload.get("case_id") or "")
        case_id = str(payload.get("case_id") or investigation_id)
        tenant_context = payload.get("tenant_context") if isinstance(payload.get("tenant_context"), dict) else {}
        record = self.investigations.save_lifecycle(
            investigation_id=investigation_id, case_id=case_id,
            tenant_id=tenant_id or tenant_context.get("tenant_id"),
            actor_id=actor_id or tenant_context.get("actor_id"),
            correlation_id=correlation_id or (payload.get("metadata") or {}).get("correlation_id"),
            status="completed" if payload.get("success") and payload.get("status") == "completed" else "failed",
            result=payload,
        )
        try:
            from services.observability import ObservabilityService
            ObservabilityService().event(
                "investigation_persisted",
                investigation_id=record.get("investigation_id"),
                case_id=record.get("case_id"),
                tenant_id=record.get("tenant_id"),
                status=record.get("status"),
                result={"success": bool(payload.get("success")), "artifact_count": len(payload.get("artifacts", []) or [])},
                **({"correlation_id": correlation_id} if correlation_id else {}),
            )
        except Exception:
            pass
        return record

    def retrieve(self, investigation_id: str, *, tenant_id: str | None = None) -> dict[str, Any] | None:
        return self.investigations.get(investigation_id, tenant_id)
