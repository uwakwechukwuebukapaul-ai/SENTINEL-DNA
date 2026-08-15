class IdentityRepository:
    """In-memory default repository; all lookups require tenant scope where relevant."""
    def __init__(self): self.users = {}; self.tenants = {}; self.roles = {}; self.permissions = {}; self.sessions = {}
    def save_user(self, user): self.users[(user.tenant_id, user.user_id)] = user; return user
    def get_user(self, user_id, tenant_id): return self.users.get((tenant_id, user_id))
    def list_users(self, tenant_id): return [u for (tenant, _), u in self.users.items() if tenant == tenant_id]
    def save_tenant(self, tenant): self.tenants[tenant.tenant_id] = tenant; return tenant
    def get_tenant(self, tenant_id): return self.tenants.get(tenant_id)
    def list_tenants(self): return list(self.tenants.values())
    def save_role(self, role): self.roles[role.role_id] = role; return role
    def get_role(self, role_id): return self.roles.get(role_id)
    def save_permission(self, permission): self.permissions[permission.permission_id] = permission; return permission
    def save_session(self, session): self.sessions[(session.tenant_id, session.session_id)] = session; return session
    def get_session(self, session_id, tenant_id): return self.sessions.get((tenant_id, session_id))
