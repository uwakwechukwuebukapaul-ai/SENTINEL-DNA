class GatewayAuthorization:
    ROLE_PERMISSIONS = {"owner": {"*"}, "admin": {"*"}, "analyst": {"read", "investigate", "write"}, "viewer": {"read"}}
    def can_access(self, context, tenant_id, permission="read"):
        if not context or not context.authenticated or not context.tenant_id or context.tenant_id != tenant_id: return False
        allowed = set(context.permissions) | self.ROLE_PERMISSIONS.get(context.role, set())
        return "*" in allowed or permission in allowed
    def require(self, context, tenant_id, permission="read"):
        if not self.can_access(context, tenant_id, permission): raise PermissionError("tenant_access_denied")
        return True
