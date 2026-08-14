from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class StreamEvent:
    organization_id: str; payload: dict[str, Any]; topic: str = "telemetry"; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class StreamMetrics:
    events_processed: int = 0; failures: int = 0; total_latency_ms: float = 0; queue_depth: int = 0
    def public(self):
        value = asdict(self); value["average_latency_ms"] = round(self.total_latency_ms / self.events_processed, 2) if self.events_processed else 0; return value
