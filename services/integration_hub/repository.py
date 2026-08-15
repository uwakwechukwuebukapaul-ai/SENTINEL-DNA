class IntegrationHubRepository:
    def __init__(self): self.connectors = {}; self.events = {}
    def save_connector(self, connector): self.connectors[(connector.tenant_id, connector.connector_id)] = connector; return connector
    def get_connector(self, connector_id, tenant_id): return self.connectors.get((tenant_id, connector_id))
    def list_connectors(self, tenant_id): return [c for (t, _), c in self.connectors.items() if t == tenant_id]
    def save_event(self, event): self.events[(event.tenant_id, event.event_id)] = event; return event
    def list_events(self, tenant_id): return [e for (t, _), e in self.events.items() if t == tenant_id]
