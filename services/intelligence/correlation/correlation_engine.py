"""
Correlation Engine

Coordinates IOC matching, threat correlation,
attack story generation, confidence scoring,
and export of intelligence correlation results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ioc_matcher import IOCMatcher
from .threat_correlator import ThreatCorrelator
from .correlation_result import CorrelationResult


class CorrelationEngine:
    """
    Intelligence correlation orchestration layer.

    Responsibilities:
    - Match indicators against knowledge
    - Correlate threats and techniques
    - Generate attack narratives
    - Calculate confidence
    - Produce analyst-ready results
    """

    def __init__(
        self,
        ioc_matcher: IOCMatcher | None = None,
        threat_correlator: ThreatCorrelator | None = None,
        knowledge_graph=None,
    ):
        """
        Initialize correlation engine.
        """

        if knowledge_graph is None:
            from services.intelligence.knowledge import KnowledgeGraph

            knowledge_graph = KnowledgeGraph()


        self.knowledge_graph = knowledge_graph


        self.ioc_matcher = (
            ioc_matcher
            or IOCMatcher(
                self.knowledge_graph
            )
        )


        self.threat_correlator = (
            threat_correlator
            or ThreatCorrelator(
                self.knowledge_graph
            )
        )


        self.history: list[dict[str, Any]] = []


    def correlate(
        self,
        case_id: str,
        indicators: list[dict[str, Any]],
        techniques: list[dict[str, Any]],
        reasoning: dict[str, Any] | None = None,
    ) -> CorrelationResult:
        """
        Execute intelligence correlation.
        """

        reasoning = reasoning or {}


        matched_iocs = (
            self.ioc_matcher.match(
                indicators
            )
        )


        correlation = (
            self.threat_correlator.correlate(
                matched_iocs,
                techniques,
            )
        )


        confidence = (
            self._calculate_confidence(
                matched_iocs,
                techniques,
                reasoning,
                indicators,
            )
        )


        attack_story = (
            self._generate_attack_story(
                indicators,
                techniques,
                correlation,
            )
        )


        result = CorrelationResult(
            case_id=case_id,
            indicators=indicators,
            techniques=techniques,
            matched_iocs=matched_iocs,
            correlations=correlation,
            confidence=confidence,
            attack_story=attack_story,
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )


        self.history.append(
            result.to_dict()
        )


        return result


    def _calculate_confidence(
        self,
        matched_iocs: list[Any],
        techniques: list[dict[str, Any]],
        reasoning: dict[str, Any],
        indicators: list[dict[str, Any]] | None = None,
    ) -> float:
        """
        Calculate confidence score.

        Scoring:
        - IOC evidence: 0.5
        - ATT&CK techniques: 0.3
        - AI reasoning: 0.1
        """

        score = 0.0


        if matched_iocs or indicators:
            score += 0.5


        if techniques:
            score += 0.3


        if reasoning:
            score += 0.1


        return min(
            score,
            1.0,
        )


    def _generate_attack_story(
        self,
        indicators: list[dict[str, Any]],
        techniques: list[dict[str, Any]],
        correlation: Any,
    ) -> str:
        """
        Generate analyst-readable attack narrative.
        """

        if not indicators and not techniques:
            return (
                "No significant attack pattern identified."
            )


        return (
            "Observed activity involving "
            f"{len(indicators)} indicators "
            "and "
            f"{len(techniques)} ATT&CK techniques."
        )


    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return previous correlation results.
        """

        return self.history.copy()


    def clear_history(
        self,
    ) -> None:
        """
        Clear correlation history.
        """

        self.history.clear()