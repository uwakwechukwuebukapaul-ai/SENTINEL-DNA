"""
Sentinel DNA - Recommendation Intelligence Engine

Responsible for:

- converting investigation data into SOC actions
- generating analyst recommendations
- prioritizing response
- maintaining recommendation history
- supporting integration contracts
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class RecommendationResult:

    case_id: str

    priority: str

    recommendations: list[str]

    actions: list[str]

    automation_ready: bool

    mitre_mapping: list[str]

    metadata: dict[str, Any]


    def to_dict(self):
        return asdict(self)


    def __getitem__(
        self,
        key: str,
    ):
        return self.to_dict()[key]



class RecommendationEngine:
    """
    AI SOC recommendation engine.
    """


    def __init__(self):

        self.engine_name = (
            "sentinel-dna-recommendation-engine"
        )

        self.history = []



    def generate(
        self,
        investigation: dict[str, Any],
    ):

        normalized = self._normalize(
            investigation
        )


        case_id = normalized.get(
            "id",
            normalized.get(
                "case_id",
                "UNKNOWN",
            ),
        )


        priority = self._priority(
            normalized
        )


        recommendations = self._recommendations(
            normalized
        )


        result = RecommendationResult(

            case_id=case_id,

            priority=priority,

            recommendations=recommendations,

            actions=recommendations,

            automation_ready=(
                priority in [
                    "high",
                    "critical",
                ]
            ),

            mitre_mapping=self._mitre(
                normalized
            ),

            metadata={

                "engine":
                    self.engine_name,

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            },
        )


        self.history.append(
            result
        )


        return result.to_dict()



    def recommend(
        self,
        reasoning,
    ):

        return self.generate(
            self._normalize(
                reasoning
            )
        )



    def analyze(
        self,
        investigation,
    ):

        return self.generate(
            investigation
        )



    def _normalize(
        self,
        value,
    ):

        if isinstance(
            value,
            dict,
        ):
            return value


        if hasattr(
            value,
            "to_dict",
        ):
            return value.to_dict()


        if hasattr(
            value,
            "__dict__",
        ):
            return vars(value)


        return {}



    def _priority(
        self,
        data,
    ):

        severity = str(
            data.get(
                "severity",
                "",
            )
        ).lower()


        if severity == "critical":

            return "critical"


        if severity == "high":

            return "high"


        if data.get(
            "credential_compromise"
        ):

            return "high"


        return "low"



    def _recommendations(
        self,
        data,
    ):

        recommendations = []


        severity = str(
            data.get(
                "severity",
                "",
            )
        ).lower()



        if data.get(
            "credential_compromise"
        ):

            recommendations.extend(
                [
                    "Reset affected credentials",
                    "Review authentication logs",
                    "Enable MFA protection",
                ]
            )


        elif severity in [
            "high",
            "critical",
        ]:

            recommendations.extend(
                [
                    "IOC blocking",
                    "Escalate incident",
                    "Collect additional evidence",
                    "Begin containment process",
                ]
            )


        else:

            recommendations.append(
                "Continue monitoring"
            )


        return recommendations



    def _mitre(
        self,
        data,
    ):

        mapping = []


        if data.get(
            "credential_compromise"
        ):

            mapping.append(
                "T1078"
            )


        return mapping



    def get_history(
        self,
    ):

        return [
            item.to_dict()
            for item in self.history
        ]



    def clear_history(
        self,
    ):

        self.history.clear()