from uuid import uuid4
from .models import IntegrationConnector, IntegrationEvent, ConnectorStatus
from .registry import IntegrationHubRegistry
from .credentials import CredentialReferenceStore
from .health import IntegrationHubHealth
from .audit import IntegrationHubAudit
class IntegrationHubService:
    def __init__(self, repository=None, registry=None, audit=None):
        self.registry = registry or IntegrationHubRegistry(repository); self.credentials = CredentialReferenceStore(); self.health = IntegrationHubHealth(self.registry); self.audit = audit or IntegrationHubAudit()
    def register(self, tenant_id, name, connector_type, provider, configuration=None, credentials=None, connector_id=None):
        connector = IntegrationConnector(connector_id or str(uuid4()), tenant_id, name, connector_type, provider, configuration=configuration or {})
        self.registry.register(connector)
        if credentials is not None: self.credentials.put(connector.connector_id, credentials)
        self.audit.record("integration_registered", tenant_id=tenant_id, connector_id=connector.connector_id); return connector
    register_connector = register
    def get(self, connector_id, tenant_id): return self.registry.get(connector_id, tenant_id)
    def list(self, tenant_id): return self.registry.list(tenant_id)
    def validate(self, connector_id, tenant_id):
        adapter = self.registry.adapter(connector_id, tenant_id); connector = self.get(connector_id, tenant_id)
        if not adapter or not connector: return False
        valid = bool(adapter.validate()); connector.status = ConnectorStatus.ACTIVE if valid else ConnectorStatus.ERROR; self.audit.record("integration_validated", tenant_id=tenant_id, connector_id=connector_id, valid=valid); return valid
    def check_health(self, connector_id, tenant_id): return self.health.check(connector_id, tenant_id)
    def disable(self, connector_id, tenant_id):
        connector = self.get(connector_id, tenant_id)
        if not connector: return False
        connector.status = ConnectorStatus.DISABLED; self.audit.record("integration_disabled", tenant_id=tenant_id, connector_id=connector_id); return True
    def route_event(self, tenant_id, connector_id, event_type, payload_reference):
        connector = self.get(connector_id, tenant_id); adapter = self.registry.adapter(connector_id, tenant_id)
        if not connector or not adapter or connector.status == ConnectorStatus.DISABLED: raise PermissionError("integration_unavailable")
        event = IntegrationEvent(str(uuid4()), connector_id, tenant_id, event_type, str(payload_reference)); self.registry.repository.save_event(event); self.audit.record("integration_event_routed", tenant_id=tenant_id, connector_id=connector_id, event_id=event.event_id); return event
