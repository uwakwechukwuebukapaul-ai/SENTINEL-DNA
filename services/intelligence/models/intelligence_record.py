"""
Threat intelligence record model.
"""


from dataclasses import dataclass, field


@dataclass
class IntelligenceRecord:

    indicator: str

    indicator_type: str

    reputation: str = "unknown"

    confidence: int = 0

    malware: str | None = None

    threat_actor: str | None = None

    campaign: str | None = None

    mitre: list[str] = field(
        default_factory=list
    )


    def to_dict(
        self,
    ) -> dict:

        return {

            "indicator":
                self.indicator,

            "type":
                self.indicator_type,

            "reputation":
                self.reputation,

            "confidence":
                self.confidence,

            "malware":
                self.malware,

            "threat_actor":
                self.threat_actor,

            "campaign":
                self.campaign,

            "mitre":
                self.mitre,

        }