class TenantAuthorizationService:
    ROLE_PERMISSIONS={"owner":{"*"},"admin":{"*"},"analyst":{"cases.read","cases.write","investigations.read"},"viewer":{"cases.read","investigations.read"}}
    def can_access_tenant(self,context,tenant_id): return bool(context and context.tenant_id==tenant_id)
    def can_access_resource(self,context,tenant_id,permission): return self.can_access_tenant(context,tenant_id) and ("*" in self.ROLE_PERMISSIONS.get(context.role,set()) or permission in self.ROLE_PERMISSIONS.get(context.role,set()))
    def require_permission(self,context,tenant_id,permission):
        if not self.can_access_resource(context,tenant_id,permission): raise PermissionError("tenant_access_denied")
        return True


class CanonicalTenantAuthorizationService(TenantAuthorizationService):
    """Fail-closed authorization adapter backed by canonical authority records."""

    def __init__(self, canonical_authority):
        if canonical_authority is None or not hasattr(canonical_authority, "resolve"):
            raise ValueError("canonical_authority_required")
        self.canonical_authority = canonical_authority

    def _canonical(self, context, tenant_id):
        if not context or not str(getattr(context, "tenant_id", "") or "").strip():
            raise PermissionError("canonical_tenant_required")
        if not str(getattr(context, "actor_id", "") or "").strip():
            raise PermissionError("canonical_actor_required")
        if str(context.tenant_id) != str(tenant_id):
            raise PermissionError("tenant_access_denied")
        try:
            return self.canonical_authority.resolve(str(tenant_id), str(context.actor_id))
        except Exception as exc:
            raise PermissionError("canonical_authority_denied") from exc

    def can_access_tenant(self, context, tenant_id):
        try:
            self._canonical(context, tenant_id)
            return True
        except PermissionError:
            return False

    def can_access_resource(self, context, tenant_id, permission):
        try:
            _, _, membership = self._canonical(context, tenant_id)
        except PermissionError:
            return False
        role = membership.role
        return "*" in self.ROLE_PERMISSIONS.get(role, set()) or permission in self.ROLE_PERMISSIONS.get(role, set())

    def require_permission(self, context, tenant_id, permission):
        self._canonical(context, tenant_id)
        if not self.can_access_resource(context, tenant_id, permission):
            raise PermissionError("tenant_access_denied")
        return True
