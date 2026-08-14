from .connector import BaseConnector
from .registry import IntegrationRegistry
from .health import IntegrationHealthService
from .audit import IntegrationAuditLogger
class IntegrationService:
    def __init__(self,registry=None): self.registry=registry or IntegrationRegistry(); self.health=IntegrationHealthService(self.registry); self.audit=IntegrationAuditLogger(); self.connectors={}
    def register(self,connector): self.connectors[connector.connector_id]=connector; self.registry.register_connector(connector); self.audit.record("connector_created",connector_id=connector.connector_id); return connector
    def enable(self,i): self.connectors[i].enabled=True; self.audit.record("connector_enabled",connector_id=i); return self.connectors[i]
    def disable(self,i): self.connectors[i].enabled=False; self.audit.record("connector_disabled",connector_id=i); return self.connectors[i]
    def test_connection(self,i): return self.health.check_connector(i)
    def get_status(self,i): return self.connectors.get(i)
    def send_event(self,i,payload): self.audit.record("send_attempt",connector_id=i); return self.connectors[i].send(payload)
    def receive_event(self,i): self.audit.record("receive_attempt",connector_id=i); return self.connectors[i].receive()
