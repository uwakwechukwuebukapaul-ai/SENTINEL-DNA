"""Read-only canonical boundary for the legacy decision feedback store."""

from __future__ import annotations

from typing import Any, Callable

from .adapters import feedback_from_store_record
from .models import Feedback


class FeedbackReadBoundary:
    """Expose legacy feedback only through verified tenant identity."""

    def __init__(
        self,
        store: Any,
        tenant_to_organization: Callable[[str], Any],
        authorization: Any,
    ) -> None:
        if store is None or not hasattr(store, "list"):
            raise ValueError("feedback_store_required")
        if not callable(tenant_to_organization):
            raise ValueError("tenant_organization_mapping_required")
        if authorization is None or not hasattr(authorization, "require_permission"):
            raise ValueError("tenant_authorization_required")
        self.store = store
        self.tenant_to_organization = tenant_to_organization
        self.authorization = authorization

    def list(self, context: Any) -> list[Feedback]:
        tenant_id = str(getattr(context, "tenant_id", "") or "").strip()
        actor_id = str(getattr(context, "actor_id", "") or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        if not actor_id:
            raise ValueError("actor_id_required")
        self.authorization.require_permission(context, tenant_id, "investigations.read")
        organization_id = str(self.tenant_to_organization(tenant_id) or "").strip()
        if not organization_id or organization_id == tenant_id:
            raise ValueError("tenant_organization_mapping_invalid")
        values: list[Feedback] = []
        for record in self.store.list(organization_id):
            normalized = dict(record)
            normalized["tenant_id"] = tenant_id
            values.append(feedback_from_store_record(normalized))
        return values
