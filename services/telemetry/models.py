from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
@dataclass
class NormalizedEvent:
    timestamp: str; source: str; hostname: str; user: str; event_type: str; severity: str; raw_data: Any; id: str = None
    def __post_init__(self): self.id = self.id or str(uuid4())
    def public(self): return asdict(self)
