"""Read-only report projection over canonical investigation state."""
from __future__ import annotations

from typing import Any

from services.core.serialization import serialize
from .investigation_projection import InvestigationProjectionBuilder, InvestigationProjectionV1


# Compatibility import name retained for callers of the previous projection.
InvestigationReportProjection = InvestigationProjectionV1


class AIInvestigatorReportService:
    """Project persisted coordinator/read-model data without executing work."""

    def build(self, coordinator: Any, investigation_id: str, tenant_id: str, context: Any) -> InvestigationProjectionV1 | None:
        try:
            view = coordinator.get_investigation_view(investigation_id, context)
        except (LookupError, PermissionError, ValueError):
            return None
        if not view:
            return None
        view = serialize(view) or {}
        return InvestigationProjectionBuilder().build_from_read_model(view, tenant_id=str(tenant_id))
