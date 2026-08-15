from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
class ConnectorType: SIEM="SIEM"; EDR="EDR"; CLOUD="CLOUD"; IDENTITY="IDENTITY"; THREAT_INTELLIGENCE="THREAT_INTELLIGENCE"; COMMUNICATION="COMMUNICATION"; CUSTOM="CUSTOM"
class ConnectorStatus: ACTIVE="ACTIVE"; DISABLED="DISABLED"; ERROR="ERROR"; PENDING="PENDING"
@dataclass
class IntegrationConnector:
    connector_id: str; tenant_id: str; name: str; connector_type: str; provider: str; status: str = ConnectorStatus.PENDING; created_at: str = field(default_factory=now); last_health_check: str | None = None; configuration: dict = field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class IntegrationEvent:
    event_id: str; connector_id: str; tenant_id: str; event_type: str; payload_reference: str; timestamp: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class IntegrationHealth:
    connector_id: str; status: str; message: str = ""; checked_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
