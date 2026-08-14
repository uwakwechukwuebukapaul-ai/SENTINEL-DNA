class TenantAuthorizationService:
    ROLE_PERMISSIONS={"owner":{"*"},"admin":{"*"},"analyst":{"cases.read","cases.write","investigations.read"},"viewer":{"cases.read","investigations.read"}}
    def can_access_tenant(self,context,tenant_id): return bool(context and context.tenant_id==tenant_id)
    def can_access_resource(self,context,tenant_id,permission): return self.can_access_tenant(context,tenant_id) and ("*" in self.ROLE_PERMISSIONS.get(context.role,set()) or permission in self.ROLE_PERMISSIONS.get(context.role,set()))
    def require_permission(self,context,tenant_id,permission):
        if not self.can_access_resource(context,tenant_id,permission): raise PermissionError("tenant_access_denied")
        return True
