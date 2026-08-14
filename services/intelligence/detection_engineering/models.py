from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class DetectionRule:
    id: str; name: str; description: str; severity: str; confidence: float; status: str; category: str; mitre_techniques: list[str]; rule_logic: dict[str, Any]; created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat()); updated_at: str = ""; synthetic_only: bool = True
    def to_dict(self): return asdict(self)
@dataclass
class DetectionResult:
    rule_id: str; matched: bool; score: float; evidence: list[Any] = field(default_factory=list); timestamp: str = ""; metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class DetectionEvaluation:
    event_id: str; matched_rules: list[str] = field(default_factory=list); detection_count: int = 0; highest_severity: str = "low"; confidence: float = 0.0; synthetic_only: bool = True
    def to_dict(self): return asdict(self)
