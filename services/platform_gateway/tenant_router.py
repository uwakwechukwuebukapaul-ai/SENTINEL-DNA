class TenantRouter:
    def __init__(self, authorization=None):
        from .authorization import GatewayAuthorization
        self.authorization = authorization or GatewayAuthorization()
    def route(self, context, tenant_id, handler, *args, permission="read", **kwargs):
        self.authorization.require(context, tenant_id, permission)
        return handler(*args, tenant_id=tenant_id, **kwargs)
