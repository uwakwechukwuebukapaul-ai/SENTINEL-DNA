from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(frozen=True)
class SigmaRule:
    title: str
    logsource: dict[str, str]
    detection: dict[str, Any]
    level: str = "medium"
    tags: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class DetectionRecommendation:
    title: str
    rationale: str
    rule: SigmaRule
    metadata: dict[str, Any] = field(default_factory=dict)
