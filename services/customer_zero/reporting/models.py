from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
@dataclass
class CustomerZeroReport:
    organization_id: str; scenario: str; attack_summary: Any; detections: list[Any]; investigations: list[Any]; mitre_techniques: list[str]; ai_analysis: Any; response_actions: Any; metrics: dict[str, Any]; security_score: float; report_id: str = field(default_factory=lambda: str(uuid4())); generated_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def public(self): return asdict(self)
