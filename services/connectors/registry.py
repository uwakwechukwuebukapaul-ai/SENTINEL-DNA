from .adapters import SyslogConnector, RestApiConnector, WebhookConnector, MicrosoftSentinelConnector, DefenderConnector
from .models import Connector, now
ADAPTERS = {"syslog": SyslogConnector, "rest_api": RestApiConnector, "webhook": WebhookConnector, "microsoft_sentinel": MicrosoftSentinelConnector, "defender": DefenderConnector}
class ConnectorRegistry:
    def __init__(self): self.items = {}
    def create(self, name, connector_type, organization_id, config=None):
        if not str(name).strip() or connector_type not in ADAPTERS or not organization_id: raise ValueError("invalid_connector")
        item = Connector(str(name).strip(), connector_type, organization_id, config or {}); self.items[item.id] = item; return item
    def list(self, organization_id): return [item for item in self.items.values() if item.organization_id == organization_id]
    def get(self, connector_id, organization_id):
        item = self.items.get(connector_id); return item if item and item.organization_id == organization_id else None
    def adapter(self, item): return ADAPTERS[item.connector_type](item)
    def test(self, item):
        result = self.adapter(item).health_check(); item.health = result; item.last_health_check = now(); item.status = "healthy" if result.get("healthy") else "unhealthy"; return result
    def collect(self, item):
        events = [self.adapter(item).normalize(event) for event in self.adapter(item).collect()]; item.events_collected += len(events); item.last_successful_collection = now(); return events
