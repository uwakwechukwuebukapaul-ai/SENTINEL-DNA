"""
Evaluation Report Model
"""


from dataclasses import dataclass, field
from datetime import datetime



@dataclass
class EvaluationReport:


    investigation_id: str

    score: dict = field(
        default_factory=dict
    )

    observations: list = field(
        default_factory=list
    )


    created_at: str = field(
        default_factory=lambda:
        datetime.utcnow().isoformat()
    )


    def add_observation(
        self,
        message
    ):

        self.observations.append(
            message
        )


    def to_dict(self):

        return {

            "investigation_id":
                self.investigation_id,

            "score":
                self.score,

            "observations":
                self.observations,

            "created_at":
                self.created_at
        }