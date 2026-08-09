"""
Sentinel DNA - Investigation Plan
"""


from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InvestigationPlan:
    """
    Investigation execution plan.
    """

    case_id: str = "CASE-900"

    name: str = (
        "Security Investigation"
    )

    plan_name: str = (
        "Security Investigation"
    )

    agents: list[str] = field(
        default_factory=list
    )

    stages: list[str] = field(
        default_factory=list
    )


    def add_stage(
        self,
        stage: str,
    ):
        """
        Add investigation stage.
        """

        self.stages.append(
            stage
        )


    def add_agent(
        self,
        agent: str,
    ):
        self.agents.append(
            agent
        )


    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "name":
                self.name,

            "plan_name":
                self.plan_name,

            "agents":
                self.agents,

            "stages":
                self.stages,

        }