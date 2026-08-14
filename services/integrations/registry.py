from __future__ import annotations
from .base import IntegrationAdapter
from .models import Integration
from .siem.sentinel import SentinelAdapter
from .siem.splunk import SplunkAdapter
from .siem.elastic import ElasticAdapter
from .edr.defender import DefenderAdapter
from .edr.crowdstrike import CrowdStrikeAdapter
from .edr.sentinelone import SentinelOneAdapter
from .ticketing.jira import JiraAdapter
from .ticketing.servicenow import ServiceNowAdapter

ADAPTERS = {"sentinel": SentinelAdapter, "microsoft_sentinel": SentinelAdapter, "splunk": SplunkAdapter, "elastic": ElasticAdapter, "defender": DefenderAdapter, "microsoft_defender": DefenderAdapter, "entra_id": DefenderAdapter, "aws_cloudtrail": SplunkAdapter, "azure_activity_logs": SentinelAdapter, "syslog": SplunkAdapter, "crowdstrike": CrowdStrikeAdapter, "sentinelone": SentinelOneAdapter, "jira": JiraAdapter, "servicenow": ServiceNowAdapter}
class CredentialStore:
    """Encryption provider boundary. Production deployments replace encrypt/decrypt with KMS."""
    def encrypt(self, credentials: dict) -> str:
        import base64, json
        return base64.urlsafe_b64encode(json.dumps(credentials, sort_keys=True).encode()).decode()
    def decrypt(self, payload: str) -> dict:
        import base64, json
        return json.loads(base64.urlsafe_b64decode(payload.encode()))
class IntegrationRegistry:
    def __init__(self, credential_store=None): self.items = {}; self.credentials = credential_store or CredentialStore()
    def register(self, name, provider, kind, config=None, credentials=None):
        if provider not in ADAPTERS: raise ValueError("unsupported_provider")
        ref = None
        if credentials: from .models import CredentialRef; ref = CredentialRef(provider, self.credentials.encrypt(credentials))
        item = Integration(name.strip(), provider, kind, config or {}, ref); self.items[item.id] = item; return item
    def get(self, item_id): return self.items.get(item_id)
    register_connector = lambda self, connector: self.items.setdefault(connector.connector_id, connector)
    remove_connector = lambda self, item_id: self.items.pop(item_id, None) is not None
    get_connector = lambda self, item_id: self.items.get(item_id)
    list_connectors = lambda self: list(self.items.values())
    get_capabilities = lambda self: {getattr(x, "connector_id", k): list(getattr(x, "capabilities", ())) for k, x in self.items.items()}
    def all(self): return list(self.items.values())
    def adapter(self, item): return ADAPTERS[item.provider](item)
    def test(self, item):
        from .models import now
        try:
            result = self.adapter(item).health_check(); item.status = "healthy" if result["healthy"] else "unhealthy"; item.last_error = None if result["healthy"] else "connection_failed"
        except Exception as exc: result = {"healthy": False, "error": "connection_failed"}; item.status = "unhealthy"; item.last_error = str(exc)
        item.last_checked_at = now(); return result
