class TenantRepository:
    def __init__(self): self.tenants={}; self.users={}
    def create_tenant(self,t): self.tenants[t.tenant_id]=t; return t
    def get_tenant(self,i): return self.tenants.get(i)
    def list_tenants(self): return list(self.tenants.values())
    def update_status(self,i,status): self.tenants[i].status=status; return self.tenants[i]
    def add_user(self,u): self.users[(u.tenant_id,u.user_id)]=u; return u
    def remove_user(self,t,u): return self.users.pop((t,u),None) is not None
    def get_users(self,t): return [u for (tenant,_),u in self.users.items() if tenant==t]
