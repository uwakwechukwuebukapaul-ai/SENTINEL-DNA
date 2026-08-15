from .models import Tenant
class TenantService:
    def __init__(self, repository=None, audit=None):
        from .repository import IdentityRepository
        self.repository = repository or IdentityRepository(); self.audit = audit
    def create_tenant(self, tenant_id, name, settings=None):
        if self.repository.get_tenant(tenant_id): raise ValueError("tenant_exists")
        tenant = self.repository.save_tenant(Tenant(tenant_id, name, settings=settings or {})); self._audit("tenant_created", tenant_id); return tenant
    def get_tenant(self, tenant_id): return self.repository.get_tenant(tenant_id)
    def list_tenants(self): return self.repository.list_tenants()
    def update_tenant(self, tenant_id, name=None, status=None, settings=None):
        tenant = self.repository.get_tenant(tenant_id)
        if not tenant: return None
        if name is not None: tenant.name = name
        if status is not None: tenant.status = status
        if settings is not None: tenant.settings = dict(settings)
        self._audit("tenant_updated", tenant_id); return tenant
    def _audit(self, event, tenant_id):
        if self.audit and hasattr(self.audit, "record"): self.audit.record(event, tenant_id=tenant_id)
