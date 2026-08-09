"""
Sentinel DNA Investigation Context

Shared investigation state container.

Provides a single source of truth for:
- evidence
- entities
- IOC intelligence
- timeline events
- MITRE mappings
- risk signals
- AI reasoning metadata
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InvestigationContext:
    """
    Runtime memory object for an investigation.

    Every intelligence component receives the same context
    to avoid duplicated analysis and inconsistent decisions.
    """

    def __init__(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> None:

        self.case_id = case_id

        self.alert = alert

        self.created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.evidence: list[dict[str, Any]] = []

        self.entities: list[dict[str, Any]] = []

        self.iocs: list[dict[str, Any]] = []

        self.timeline: list[dict[str, Any]] = []

        self.mitre_techniques: list[str] = []

        self.risk_signals: dict[str, Any] = {}

        self.recommendations: list[str] = []

        self.metadata: dict[str, Any] = {}



    def add_evidence(
        self,
        evidence: dict[str, Any],
    ) -> None:

        self.evidence.append(
            evidence
        )



    def add_entity(
        self,
        entity: dict[str, Any],
    ) -> None:

        self.entities.append(
            entity
        )



    def add_ioc(
        self,
        ioc: dict[str, Any],
    ) -> None:

        self.iocs.append(
            ioc
        )



    def add_timeline_event(
        self,
        event: dict[str, Any],
    ) -> None:

        self.timeline.append(
            event
        )



    def add_mitre_mapping(
        self,
        technique: str,
    ) -> None:

        if technique not in self.mitre_techniques:
            self.mitre_techniques.append(
                technique
            )



    def set_risk(
        self,
        risk_data: dict[str, Any],
    ) -> None:

        self.risk_signals = risk_data



    def add_recommendation(
        self,
        recommendation: str,
    ) -> None:

        self.recommendations.append(
            recommendation
        )



    def update_metadata(
        self,
        metadata: dict[str, Any],
    ) -> None:

        self.metadata.update(
            metadata
        )



    def snapshot(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,

            "alert": self.alert,

            "evidence": self.evidence,

            "entities": self.entities,

            "iocs": self.iocs,

            "timeline": self.timeline,

            "mitre":
                self.mitre_techniques,

            "risk":
                self.risk_signals,

            "recommendations":
                self.recommendations,

            "metadata":
                self.metadata,

            "created_at":
                self.created_at,
        }