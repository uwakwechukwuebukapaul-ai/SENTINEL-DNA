from .models import IntegrationHealth, now
class IntegrationHubHealth:
    def __init__(self, registry): self.registry = registry
    def check(self, connector_id, tenant_id):
        connector = self.registry.get(connector_id, tenant_id); adapter = self.registry.adapter(connector_id, tenant_id)
        if not connector or not adapter: return None
        try: result = adapter.health_check(); status = result.get("status", "healthy"); message = result.get("message", "")
        except Exception as exc: status, message = "error", str(exc)
        connector.last_health_check = now(); connector.status = "ACTIVE" if status == "healthy" else "ERROR"
        return IntegrationHealth(connector_id, status, message)
