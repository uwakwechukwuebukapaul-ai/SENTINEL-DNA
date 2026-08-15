from .connector import SyntheticConnector
class IntegrationHubRegistry:
    def __init__(self, repository=None):
        from .repository import IntegrationHubRepository
        self.repository = repository or IntegrationHubRepository(); self.adapters = {}
    def register(self, connector, adapter=None):
        saved = self.repository.save_connector(connector); self.adapters[(connector.tenant_id, connector.connector_id)] = adapter or SyntheticConnector(saved); return saved
    def get(self, connector_id, tenant_id): return self.repository.get_connector(connector_id, tenant_id)
    def list(self, tenant_id): return self.repository.list_connectors(tenant_id)
    def adapter(self, connector_id, tenant_id): return self.adapters.get((tenant_id, connector_id))
