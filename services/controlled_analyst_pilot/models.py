"""Public models for the controlled analyst pilot overlay."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PILOT_ANALYST_PERMISSIONS = frozenset(
    {
        "pilot:read",
        "pilot:feedback",
        "pilot:feedback:read",
        "pilot:review",
        "pilot:review:read",
        "investigations:read",
        "investigations:run",
        "reports:read",
    }
)

PILOT_MANAGER_PERMISSIONS = frozenset(
    {
        "pilot:manage",
        "pilot:feedback:read",
        "pilot:review:read",
        "pilot:review:manage",
        "pilot:audit:read",
    }
)


@dataclass(frozen=True)
class PilotTenantState:
    tenant_id: str
    manager_tenant_id: str
    display_name: str
    status: str
    expires_at: str
    provisioned_by: str
    provisioning_id: str
    analyst_id: str
    role: str = "analyst"
    synthetic_only: bool = True
    external_custody_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotReviewState:
    review_id: str
    tenant_id: str
    case_id: str
    investigation_id: str
    analyst_id: str
    status: str
    decision: str
    comments: str
    last_actor_id: str
    updated_at: str
    reversible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
