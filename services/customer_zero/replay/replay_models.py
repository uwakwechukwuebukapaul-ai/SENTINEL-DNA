from dataclasses import dataclass, asdict
@dataclass
class ReplayEvent:
    timestamp: str; stage: str; description: str; status: str = "completed"
    def public(self): return asdict(self)
