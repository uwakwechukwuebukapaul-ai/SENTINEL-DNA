"""Adapter over the canonical tenant authority for alert assignment targets."""
from __future__ import annotations


class CanonicalAssignmentDirectory:
    def __init__(self, authority):
        self.authority = authority

    def validate_target(self, *, tenant_id: str, actor_id: str):
        try:
            _tenant, identity, membership = self.authority.resolve(str(tenant_id), str(actor_id))
        except Exception as exc:
            raise PermissionError("assignment_target_not_eligible") from exc
        if str(getattr(identity, "status", "active")).lower() != "active" or str(getattr(membership, "status", "active")).lower() != "active":
            raise PermissionError("assignment_target_not_eligible")
        if str(getattr(membership, "role", "")).lower() not in {"analyst", "soc_manager", "admin"}:
            raise PermissionError("assignment_target_role_not_permitted")
        return {"actor_id": str(actor_id), "role": str(membership.role).lower(), "tenant_id": str(tenant_id)}

    def list_for_tenant(self, *, tenant_id: str):
        from database.canonical_authority import CanonicalUnitOfWork
        with CanonicalUnitOfWork(self.authority.db) as unit:
            rows = unit.connection.execute("SELECT i.actor_id, i.email, i.display_name, m.role FROM canonical_identities i JOIN canonical_memberships m ON m.actor_id=i.actor_id WHERE m.tenant_id=? AND i.status='active' AND m.status='active' AND m.role IN ('analyst','soc_manager','admin') ORDER BY i.display_name, i.actor_id", (str(tenant_id),)).fetchall()
        return [{"actor_id": row["actor_id"], "email": row["email"], "display_name": row["display_name"], "role": row["role"]} for row in rows]
