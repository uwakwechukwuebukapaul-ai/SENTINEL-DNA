"""Application-facing, tenant-scoped audit read abstraction."""

from __future__ import annotations

from typing import Any

from .service import AuditService


class ApplicationAuditReadService:
    """Expose safe application audit projections without owning persistence."""

    MAX_LIMIT = 100

    def __init__(self, audit_service: AuditService) -> None:
        self.audit_service = audit_service

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        tenant = str(tenant_id or "").strip()
        if not tenant:
            raise ValueError("tenant_context_required")
        if not isinstance(limit, int) or limit < 1 or limit > self.MAX_LIMIT:
            raise ValueError("invalid_limit")
        if event_type is not None and len(str(event_type)) > 128:
            raise ValueError("invalid_event_type")
        events = self.audit_service.list_for_tenant(
            tenant,
            event_type=str(event_type) if event_type else None,
            limit=limit,
        )
        return [self.audit_service.public_event(event) for event in events]


__all__ = ["ApplicationAuditReadService"]
