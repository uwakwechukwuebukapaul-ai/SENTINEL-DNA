"""
Simulation Result Model
"""


from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SimulationResult:

    scenario_name: str

    status: str = "completed"

    findings: list = field(
        default_factory=list
    )

    executed_steps: list = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.utcnow().isoformat()
    )


    def add_finding(self, finding):

        self.findings.append(finding)


    def add_step(self, step):

        self.executed_steps.append(step)


    def to_dict(self):

        return {

            "scenario_name":
                self.scenario_name,

            "status":
                self.status,

            "findings":
                self.findings,

            "executed_steps":
                self.executed_steps,

            "metadata":
                self.metadata,

            "created_at":
                self.created_at,
        }