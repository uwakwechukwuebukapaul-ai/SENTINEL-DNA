from .service import TenantService
class TenantMiddleware:
    def __init__(self,app,service=None): self.app=app; self.service=service or TenantService()
    def __call__(self,environ,start_response): self.service.resolve_context(environ.get("HTTP_X_USER_ID"),environ.get("HTTP_X_TENANT_ID"),environ.get("HTTP_X_REQUEST_ID")); return self.app(environ,start_response)
