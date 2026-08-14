from services.tenant import TenantService,TenantContextManager,TenantAuthorizationService
def test_tenant_creation(): assert TenantService().create_tenant("t1","Acme","acme").tenant_id == "t1"
def test_tenant_serialization(): assert "tenant_id" in TenantService().default_tenant.to_dict()
def test_user_tenant_mapping():
 s=TenantService(); s.create_tenant("t1","A","a"); assert s.add_user("t1","u").tenant_id == "t1"
def test_context_management():
 c=TenantContextManager(); c.set_context(__import__('services.tenant',fromlist=['TenantContext']).TenantContext("t")); assert c.get_context().tenant_id == "t"; c.clear_context(); assert c.get_context() is None
def test_default_tenant_fallback(): assert TenantService().resolve_context().tenant_id == "default"
def test_permission_checking():
 s=TenantService(); c=s.resolve_context("u","default"); assert TenantAuthorizationService().require_permission(c,"default","cases.read")
def test_access_denied():
 s=TenantService(); c=s.resolve_context("u","default")
 try: TenantAuthorizationService().require_permission(c,"other","cases.read"); assert False
 except PermissionError: assert True
def test_audit_logging(): s=TenantService(); s.create_tenant("t","T","t"); assert s.audit.events
def test_backward_compatibility(): assert TenantService().default_tenant.status == "active"
def test_deterministic_behavior(): assert TenantService().resolve_context().tenant_id == TenantService().resolve_context().tenant_id
