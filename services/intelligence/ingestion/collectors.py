from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4
from .models import SecurityEvent

class BaseCollector(ABC):
    def __init__(self, tenant_id=None, source="unknown"): self.tenant_id=tenant_id; self.source=source
    @abstractmethod
    def collect(self, payload: Any) -> list[SecurityEvent]: ...
    def _event(self, payload):
        data = payload if isinstance(payload, dict) else {"value": payload}
        return SecurityEvent(str(data.get("event_id") or data.get("id") or uuid4()), self.tenant_id, str(data.get("source") or self.source), str(data.get("event_type") or data.get("type") or "unknown"), data)

class SyntheticEventCollector(BaseCollector):
    def collect(self, payload): return [self._event(item) for item in (payload if isinstance(payload, list) else [payload])]

class WebhookCollector(BaseCollector):
    def collect(self, payload): return SyntheticEventCollector(self.tenant_id, self.source).collect(payload.get("events", payload) if isinstance(payload, dict) else payload)

class APICollector(BaseCollector):
    def collect(self, payload):
        if callable(payload): payload = payload()
        return SyntheticEventCollector(self.tenant_id, self.source).collect(payload)
