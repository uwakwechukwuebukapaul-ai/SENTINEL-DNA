from .models import NormalizedSecurityEvent
class IngestionRepository:
    def __init__(self): self._events: dict[str | None, list[NormalizedSecurityEvent]] = {}
    def save(self, event): self._events.setdefault(event.tenant_id, []).append(event); return event
    def list(self, tenant_id): return list(self._events.get(tenant_id, []))
