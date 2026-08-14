from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from .models import Integration

class IntegrationAdapter(ABC):
    provider = "generic"; kind = "generic"
    def __init__(self, integration: Integration): self.integration = integration
    @abstractmethod
    def connect(self) -> dict[str, Any]: ...
    def validate(self) -> dict[str, Any]:
        if not self.integration.config: return {"valid": False, "error": "missing_configuration"}
        return {"valid": True, "provider": self.provider}
    def ingest(self, payload: Any = None) -> dict[str, Any]: return {"provider": self.provider, "operation": "ingest", "items": payload or []}
    def normalize(self, payload: Any) -> dict[str, Any]:
        from .siem.normalizer import normalize_event
        return normalize_event(payload, self.provider).public()
    def send(self, payload: Any = None) -> dict[str, Any]: return {"provider": self.provider, "operation": "send", "accepted": True, "payload": payload or {}}
    def health_check(self):
        result = self.connect(); return {"healthy": bool(result.get("connected")), **result}

class MockEnterpriseAdapter(IntegrationAdapter):
    def connect(self): return {"connected": True, "provider": self.provider, "mode": "mock"}
