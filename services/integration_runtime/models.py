from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
class ExecutionStatus: QUEUED="QUEUED"; RUNNING="RUNNING"; SUCCESS="SUCCESS"; FAILED="FAILED"; RETRYING="RETRYING"
@dataclass
class ConnectorExecution:
    execution_id: str; connector_id: str; tenant_id: str; operation: str; status: str = ExecutionStatus.QUEUED; started_at: str = field(default_factory=now); completed_at: str | None = None; error_message: str = ""; attempts: int = 0
    def to_dict(self): return asdict(self)
@dataclass
class DataExchangeEvent:
    exchange_id: str; connector_id: str; tenant_id: str; event_type: str; payload_reference: str; timestamp: str = field(default_factory=now); normalized: bool = False
    def to_dict(self): return asdict(self)
