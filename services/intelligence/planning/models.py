from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class InvestigationPlan:
    case_id: str
    objective: str
    tasks: list[str] = field(default_factory=list)
    priority: str = "medium"
    confidence: float = 0.0

    def public(self) -> dict:
        return {"case_id": self.case_id, "objective": self.objective, "tasks": list(self.tasks), "priority": self.priority, "confidence": self.confidence}
