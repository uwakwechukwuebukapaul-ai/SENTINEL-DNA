"""
Sentinel DNA Investigation Plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationPlan:
    case_id: str = "CASE-900"

    name: str = "Security Investigation"

    plan_name: str = "Security Investigation"

    agents: list[str] = field(
        default_factory=list
    )

    stages: list[str] = field(
        default_factory=list
    )

    def add_stage(
        self,
        stage: str,
    ) -> None:

        if stage:
            self.stages.append(str(stage))

    def add_agent(
        self,
        agent: str,
    ) -> None:

        if agent:
            self.agents.append(str(agent))

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "name": self.name,
            "plan_name": self.plan_name,
            "agents": list(self.agents),
            "stages": list(self.stages),
        }


__all__ = [
    "InvestigationPlan",
]
