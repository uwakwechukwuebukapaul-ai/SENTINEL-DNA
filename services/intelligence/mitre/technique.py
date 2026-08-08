"""
Sentinel DNA MITRE Technique Model
"""

from dataclasses import dataclass


@dataclass
class MitreTechnique:

    technique_id: str

    name: str

    tactic: str

    description: str = ""


    def to_dict(self):

        return {

            "id":
                self.technique_id,

            "name":
                self.name,

            "tactic":
                self.tactic,

            "description":
                self.description,
        }