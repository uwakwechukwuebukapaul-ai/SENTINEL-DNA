from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class Connector:
    name: str; connector_type: str; organization_id: str; config: dict[str, Any] = field(default_factory=dict); id: str = field(default_factory=lambda: str(uuid4())); status: str = "configured"; last_successful_collection: str | None = None; last_health_check: str | None = None; health: dict[str, Any] = field(default_factory=dict); events_collected: int = 0
    def public(self):
        value = asdict(self); value["config"] = {key: val for key, val in self.config.items() if key not in {"token", "password", "secret", "api_key"}}; return value
