class IdentityPolicy:
    """Identity-backed policy seam consumed by gateway authorization adapters."""
    def __init__(self, repository): self.repository = repository
    def can(self, user_id, tenant_id, resource, action):
        user = self.repository.get_user(user_id, tenant_id)
        if not user or user.status != "active": return False
        wanted = f"{resource}:{action}"
        for role_id in user.roles:
            role = self.repository.get_role(role_id)
            if role and ("*: *" in role.permissions or "*:*" in role.permissions or wanted in role.permissions or action in role.permissions): return True
        return False
    def require(self, user_id, tenant_id, resource, action):
        if not self.can(user_id, tenant_id, resource, action): raise PermissionError("identity_policy_denied")
        return True
