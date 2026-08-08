"""
Sentinel DNA MITRE Tactic Model
"""


from dataclasses import dataclass



@dataclass
class MitreTactic:


    name: str


    description: str = ""



    def to_dict(self):

        return {

            "name":
                self.name,

            "description":
                self.description,
        }