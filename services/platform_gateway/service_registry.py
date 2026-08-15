class GatewayServiceRegistry:
    """Names only existing service objects; it owns no domain behavior."""
    def __init__(self): self._services = {}
    def register(self, name, service):
        if not name or service is None: raise ValueError("invalid_service")
        self._services[str(name)] = service; return service
    def get(self, name): return self._services.get(name)
    def has(self, name): return name in self._services
    def all(self): return dict(self._services)
    def health(self, name):
        service = self.get(name)
        if service is None: return False
        check = getattr(service, "health", None)
        return bool(check()) if callable(check) else True
