from .models import Tenant,TenantUser,TenantContext
from .repository import TenantRepository
from .context import TenantContextManager
from .audit import TenantAuditLogger
class TenantService:
    def __init__(self,repository=None): self.repository=repository or TenantRepository(); self.context=TenantContextManager(); self.audit=TenantAuditLogger(); self.default_tenant=self.repository.create_tenant(Tenant("default","Development","development"))
    def create_tenant(self,tenant_id,name,slug,metadata=None): t=self.repository.create_tenant(Tenant(tenant_id,name,slug,metadata=metadata or {})); self.audit.record("tenant_created",tenant_id=tenant_id); return t
    def add_user(self,tenant_id,user_id,role="viewer",permissions=None): u=self.repository.add_user(TenantUser(tenant_id,user_id,role,permissions or [])); self.audit.record("user_added",tenant_id=tenant_id,user_id=user_id); return u
    def resolve_context(self,user_id=None,tenant_id=None,request_id=""): return self.context.set_context(TenantContext(tenant_id or "default",user_id,"viewer",request_id))
