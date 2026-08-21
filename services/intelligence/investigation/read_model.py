"""Tenant-scoped analyst read model for the canonical investigation path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InvestigationReadModel:
    """A deterministic composition of already-authorized investigation data."""

    investigation: dict[str, Any]
    report: dict[str, Any]
    intelligence: dict[str, Any]
    quality: dict[str, Any]
    feedback: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation": self.investigation,
            "report": self.report,
            "intelligence": self.intelligence,
            "quality": self.quality,
            "feedback": self.feedback,
        }


class InvestigationReadModelBuilder:
    """Compose the analyst view using tenant-scoped repository reads only."""

    def __init__(
        self,
        report_repository: Any,
        intelligence_repository: Any,
        quality_repository: Any,
        feedback_repository: Any,
    ) -> None:
        self.report_repository = report_repository
        self.intelligence_repository = intelligence_repository
        self.quality_repository = quality_repository
        self.feedback_repository = feedback_repository

    def build(self, case_id: str, tenant_id: str) -> InvestigationReadModel | None:
        case_id = str(case_id or "").strip()
        tenant_id = str(tenant_id or "").strip()
        if not case_id or not tenant_id:
            return None

        report = self._for_tenant(self.report_repository, case_id, tenant_id)
        if not isinstance(report, dict):
            return None
        intelligence = self._for_tenant(self.intelligence_repository, case_id, tenant_id) or {}
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        assessment = self.quality_repository.get_assessment(tenant_id, investigation_id)
        feedback = self.feedback_repository.list_for_investigation(tenant_id, investigation_id)

        return InvestigationReadModel(
            investigation={
                "id": investigation_id,
                "case_id": case_id,
                "tenant_id": tenant_id,
                "status": report.get("status", "unknown"),
            },
            report=report,
            intelligence=intelligence,
            quality=assessment.to_dict() if assessment else {},
            feedback=[item.to_dict() for item in feedback],
        )

    @staticmethod
    def _for_tenant(repository: Any, case_id: str, tenant_id: str) -> dict[str, Any] | None:
        getter = getattr(repository, "get_by_case_id_for_tenant", None)
        if not callable(getter):
            raise RuntimeError("tenant-scoped investigation repository is required")
        value = getter(case_id, tenant_id)
        return value if isinstance(value, dict) else None


__all__ = ["InvestigationReadModel", "InvestigationReadModelBuilder"]
