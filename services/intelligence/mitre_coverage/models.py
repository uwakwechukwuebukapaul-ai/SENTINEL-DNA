from dataclasses import asdict, dataclass, field
@dataclass
class DetectionGapReport:
    missing_techniques: list[str]=field(default_factory=list); affected_tactics: list[str]=field(default_factory=list); recommendation: str=""; priority: str="low"
    def to_dict(self): return asdict(self)
