from .models import ServiceHealth
class GatewayHealthChecker:
    def __init__(self, registry): self.registry = registry
    def check(self): return [ServiceHealth(name, "healthy" if self.registry.health(name) else "unhealthy") for name in self.registry.all()]
