from abc import ABC, abstractmethod
from typing import Any
from .models import Connector
class ConnectorAdapter(ABC):
    def __init__(self, connector: Connector): self.connector = connector
    @abstractmethod
    def connect(self): ...
    def authenticate(self): return {"authenticated": True, "mode": "managed"}
    def health_check(self): return {"healthy": bool(self.connect().get("connected")), "connector_type": self.connector.connector_type}
    def collect(self): return []
    def normalize(self, event: dict[str, Any]): return {**event, "organization_id": self.connector.organization_id, "source": self.connector.connector_type}
class MockConnector(ConnectorAdapter):
    def connect(self): return {"connected": True, "mode": "mock", "connector_type": self.connector.connector_type}
    def collect(self): return self.connector.config.get("events", [])
