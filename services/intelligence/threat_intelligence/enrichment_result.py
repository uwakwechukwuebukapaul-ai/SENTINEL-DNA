"""
Threat Intelligence Enrichment Result.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThreatIntelligenceResult:

    success: bool = True

    iocs: list[dict[str, Any]] = field(
        default_factory=list
    )

    reputation: dict[str, Any] = field(
        default_factory=dict
    )

    mitre_attack: list[str] = field(
        default_factory=list
    )

    threat_profile: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {

            "success":
                self.success,

            "iocs":
                self.iocs,

            "reputation":
                self.reputation,

            "mitre_attack":
                self.mitre_attack,

            "threat_profile":
                self.threat_profile,

            "metadata":
                self.metadata,

        }