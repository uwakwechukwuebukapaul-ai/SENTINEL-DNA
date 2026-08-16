"""Fail-closed administrative lifecycle for external identity bindings."""
from __future__ import annotations
from database.canonical_authority import CanonicalIdentityBindingRepository, CanonicalIdentityRepository, CanonicalMembershipRepository, CanonicalUnitOfWork
from database.connection import DatabaseConnection, database
from .bindings import IdentityBinding, IdentityBindingError, _binding


class IdentityBindingAdministrationService:
    ADMIN_PERMISSION = "identity.bindings.manage"

    def __init__(self, authorization, db: DatabaseConnection = database, audit=None):
        if authorization is None or not hasattr(authorization, "require_permission"): raise ValueError("canonical_authorization_required")
        self.authorization, self.db, self.audit = authorization, db, audit

    def _authorize(self, context, actor_id, memberships):
        if not context or not getattr(context, "tenant_id", "") or not getattr(context, "actor_id", ""): raise PermissionError("canonical_context_required")
        self.authorization.require_permission(context, context.tenant_id, self.ADMIN_PERMISSION)
        target = memberships.get(context.tenant_id, actor_id)
        if not target or target["status"] != "active": raise PermissionError("binding_target_outside_tenant")

    def create_binding(self, context, provider, external_subject, actor_id, created_by):
        provider, external_subject, actor_id, created_by = [str(v or "").strip() for v in (provider, external_subject, actor_id, created_by)]
        if not all((provider, external_subject, actor_id, created_by)): raise IdentityBindingError("binding_fields_required")
        with CanonicalUnitOfWork(self.db) as unit:
            self._authorize(context, actor_id, CanonicalMembershipRepository(unit.conn))
            identity = CanonicalIdentityRepository(unit.conn).get(actor_id)
            if not identity or identity["status"] != "active": raise IdentityBindingError("canonical_actor_inactive")
            try: row = CanonicalIdentityBindingRepository(unit.conn).create(provider, external_subject, actor_id, created_by)
            except Exception as exc: raise IdentityBindingError("identity_binding_rejected") from exc
            self._audit(unit.conn, "IDENTITY_BINDING_CREATED", row, context)
            return _binding(row)

    def disable_binding(self, context, binding_id): return self._transition(context, binding_id, "disabled")
    def reactivate_binding(self, context, binding_id): return self._transition(context, binding_id, "active")
    def revoke_binding(self, context, binding_id): return self._transition(context, binding_id, "revoked")

    def _transition(self, context, binding_id, new_status):
        with CanonicalUnitOfWork(self.db) as unit:
            bindings = CanonicalIdentityBindingRepository(unit.conn); current = bindings.get_by_id(binding_id)
            if not current: raise IdentityBindingError("identity_binding_not_found")
            self._authorize(context, current["actor_id"], CanonicalMembershipRepository(unit.conn))
            allowed = {"active": {"disabled", "revoked"}, "disabled": {"active", "revoked"}, "revoked": set()}
            if new_status not in allowed[current["status"]]: raise IdentityBindingError("invalid_binding_transition")
            row = bindings.set_status(binding_id, new_status); self._audit(unit.conn, f"IDENTITY_BINDING_{new_status.upper()}", row, context); return _binding(row)

    def _audit(self, connection, event, row, context):
        if self.audit: self.audit.record(event, details={"binding_id": row["binding_id"], "provider": row["provider"], "actor_id": row["actor_id"], "acting_actor_id": context.actor_id, "tenant_id": context.tenant_id}, connection=connection)

