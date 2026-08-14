from dataclasses import asdict, dataclass, field

@dataclass
class BehaviorFinding:
    event: dict; risk_score: float; reason: str; confidence: float; mitre_mapping: list[str] = field(default_factory=list)
    def public(self): return asdict(self)
