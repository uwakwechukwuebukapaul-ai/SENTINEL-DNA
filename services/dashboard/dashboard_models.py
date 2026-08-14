from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class DashboardSnapshot:
    metrics: dict[str, Any]
    investigations: list[dict[str, Any]] = field(default_factory=list)
    iocs: list[dict[str, Any]] = field(default_factory=list)
    techniques: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"metrics": self.metrics, "investigations": self.investigations,
                "iocs": self.iocs, "techniques": self.techniques, "timeline": self.timeline}
