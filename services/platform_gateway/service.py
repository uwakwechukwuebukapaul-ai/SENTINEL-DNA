from uuid import uuid4
from .models import APIResponse
from .authorization import GatewayAuthorization
from .tenant_router import TenantRouter
from .service_registry import GatewayServiceRegistry
from .audit_middleware import GatewayAuditLogger
from .health import GatewayHealthChecker
class PlatformGateway:
    def __init__(self, registry=None, authorization=None, audit_logger=None):
        self.registry = registry or GatewayServiceRegistry(); self.authorization = authorization or GatewayAuthorization(); self.router = TenantRouter(self.authorization); self.audit = audit_logger or GatewayAuditLogger(); self.health = GatewayHealthChecker(self.registry)
    def dispatch(self, context, service_name, method, *args, tenant_id=None, permission="read", **kwargs):
        request_id = getattr(context, "request_id", str(uuid4()))
        try:
            if not tenant_id: raise PermissionError("tenant_required")
            service = self.registry.get(service_name)
            if service is None: raise LookupError("service_not_found")
            handler = getattr(service, method)
            result = self.router.route(context, tenant_id, handler, *args, permission=permission, **kwargs)
            self.audit.record("gateway_request_completed", context=context, tenant_id=tenant_id, service=service_name, method=method)
            return APIResponse(True, result, request_id=request_id)
        except (PermissionError, LookupError, AttributeError) as exc:
            self.audit.record("gateway_request_denied", context=context, tenant_id=tenant_id, service=service_name, error=str(exc))
            return APIResponse(False, error=str(exc), request_id=request_id)
