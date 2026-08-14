from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
@dataclass
class DetectionSuggestion:
    organization_id: str; name: str; description: str; reason: str; query_logic: dict; sigma_rule: dict; mitre_mapping: list; confidence: float; status: str="GENERATED"; id: str=field(default_factory=lambda:str(uuid4())); created_at: str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    def public(self): return asdict(self)
