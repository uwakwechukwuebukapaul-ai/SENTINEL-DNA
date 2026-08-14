from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    tenant_id: str | None
    source: str
    event_type: str
    payload: dict[str, Any]
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class NormalizedSecurityEvent:
    event_id: str
    tenant_id: str | None
    category: str
    event_type: str
    timestamp: str
    source: str
    fields: dict[str, Any] = field(default_factory=dict)
    raw_event_id: str | None = None
    def to_dict(self): return asdict(self)

@dataclass
class IngestionBatch:
    batch_id: str
    tenant_id: str | None
    event_count: int = 0
    normalized_count: int = 0
    failed_count: int = 0
    status: str = "completed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class IngestionMetrics:
    received: int = 0
    normalized: int = 0
    failed: int = 0
    routed: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    def to_dict(self): return asdict(self)
