from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class ValidationResult:
    campaign_id: str; detected_techniques: list[str]; missed_techniques: list[str]; technique_coverage: dict[str, Any]; tactic_coverage: dict[str, Any]; scores: dict[str, float]; gaps: list[dict[str, Any]]; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
