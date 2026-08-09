"""
Sentinel DNA Investigation Result

Enterprise investigation output model.

Represents normalized output from:
- Evidence Intelligence
- Threat Intelligence
- MITRE Mapping
- Risk Analysis
- Recommendations
- Autonomous Investigation Agents
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InvestigationResult:
    """
    Standardized AI investigation result.
    """

    def __init__(
        self,
        case_id: str,
        status: str = "completed",
    ) -> None:

        self.case_id = case_id
        self.status = status

        self.created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.findings: dict[str, Any] = {}

        self.iocs: list[
            dict[str, Any]
        ] = []

        self.entities: list[
            dict[str, Any]
        ] = []

        self.mitre_attack: list[str] = []

        self.timeline: list[
            dict[str, Any]
        ] = []

        self.recommendations: list[str] = []

        self.risk_score: int = 0

        self.confidence: float = 0.0

        self.metadata: dict[str, Any] = {}


    def add_finding(
        self,
        name: str,
        result: Any,
    ) -> None:
        """
        Add intelligence finding.
        """

        self.findings[name] = result


    def add_ioc(
        self,
        ioc: dict[str, Any],
    ) -> None:
        """
        Add indicator of compromise.
        """

        if ioc not in self.iocs:
            self.iocs.append(ioc)


    def add_entity(
        self,
        entity: dict[str, Any],
    ) -> None:
        """
        Add discovered entity.
        """

        if entity not in self.entities:
            self.entities.append(entity)


    def add_mitre(
        self,
        technique: str,
    ) -> None:
        """
        Add MITRE ATT&CK technique.
        """

        if technique not in self.mitre_attack:
            self.mitre_attack.append(
                technique
            )


    def add_timeline_event(
        self,
        event: dict[str, Any],
    ) -> None:
        """
        Add investigation timeline event.
        """

        self.timeline.append(event)


    def add_recommendation(
        self,
        recommendation: str,
    ) -> None:
        """
        Add analyst recommendation.
        """

        if recommendation not in self.recommendations:
            self.recommendations.append(
                recommendation
            )


    def set_risk(
        self,
        score: int,
        confidence: float = 0.0,
    ) -> None:
        """
        Set risk evaluation.
        """

        self.risk_score = score
        self.confidence = confidence


    def update_metadata(
        self,
        data: dict[str, Any],
    ) -> None:
        """
        Attach investigation metadata.
        """

        self.metadata.update(data)


    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert result into API/report format.
        """

        return {

            "case_id":
                self.case_id,

            "status":
                self.status,

            "created_at":
                self.created_at,

            "findings":
                self.findings,

            "iocs":
                self.iocs,

            "entities":
                self.entities,

            "mitre_attack":
                self.mitre_attack,

            "risk_score":
                self.risk_score,

            "confidence":
                self.confidence,

            "timeline":
                self.timeline,

            "recommendations":
                self.recommendations,

            "metadata":
                self.metadata,

            "summary": {

                "ioc_count":
                    len(self.iocs),

                "entity_count":
                    len(self.entities),

                "mitre_count":
                    len(self.mitre_attack),

                "timeline_events":
                    len(self.timeline),

                "recommendation_count":
                    len(self.recommendations),

            }
        }