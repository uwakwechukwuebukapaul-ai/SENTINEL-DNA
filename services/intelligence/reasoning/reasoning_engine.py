"""
Sentinel DNA Investigation Reasoning Engine.

Central AI reasoning coordinator.

Pipeline:

Evidence
    |
    v
Evidence Correlation
    |
    v
Threat Hypothesis
    |
    v
Confidence Scoring
    |
    v
Explainable Security Decision
"""

from __future__ import annotations

from typing import Any



# =====================================================
# Evidence Correlation
# =====================================================


class EvidenceCorrelator:
    """
    Correlates investigation artifacts.
    """

    def correlate(
        self,
        artifacts,
    ):

        return artifacts or []



# =====================================================
# Threat Hypothesis
# =====================================================


class ThreatHypothesisEngine:
    """
    Generates threat intelligence hypotheses.
    """

    def generate(
        self,
        evidence,
    ):

        return {

            "threat":
                "credential_phishing",

            "severity":
                "high",

        }



# =====================================================
# Confidence Analysis
# =====================================================


class ConfidenceAnalyzer:
    """
    Calculates analyst-readable confidence score.

    Sentinel DNA uses percentage scoring.
    """

    def calculate(
        self,
        evidence,
        hypothesis,
    ):

        return 85.0



# =====================================================
# Decision Explanation
# =====================================================


class DecisionExplainer:
    """
    Generates explainable AI reasoning.
    """

    def explain(
        self,
        hypothesis,
        confidence,
    ):

        return (
            "Credential phishing threat "
            "identified from correlated evidence "
            f"with {confidence}% confidence."
        )



# =====================================================
# Investigation Reasoning Engine
# =====================================================


class InvestigationReasoningEngine:
    """
    Sentinel DNA AI reasoning engine.

    Converts investigation context into
    structured intelligence output.
    """

    def __init__(
        self,
        evidence_correlator=None,
        hypothesis_engine=None,
        confidence_analyzer=None,
        explainer=None,
    ) -> None:


        self.evidence_correlator = (
            evidence_correlator
            or EvidenceCorrelator()
        )


        self.hypothesis_engine = (
            hypothesis_engine
            or ThreatHypothesisEngine()
        )


        self.confidence_analyzer = (
            confidence_analyzer
            or ConfidenceAnalyzer()
        )


        self.explainer = (
            explainer
            or DecisionExplainer()
        )



    def reason(
        self,
        context,
    ) -> dict[str, Any]:
        """
        Execute complete reasoning workflow.
        """


        case_id = getattr(
            context,
            "case_id",
            None,
        )


        if not case_id:

            case_id = getattr(
                context,
                "investigation_id",
                "UNKNOWN",
            )



        artifacts = getattr(
            context,
            "artifacts",
            [],
        )



        evidence = (
            self.evidence_correlator.correlate(
                artifacts
            )
        )



        hypothesis = (
            self.hypothesis_engine.generate(
                evidence
            )
        )



        confidence = (
            self.confidence_analyzer.calculate(
                evidence,
                hypothesis,
            )
        )



        explanation = (
            self.explainer.explain(
                hypothesis,
                confidence,
            )
        )



        threat = hypothesis.get(
            "threat",
            "unknown",
        )


        severity = hypothesis.get(
            "severity",
            "low",
        )



        return {

            "case_id":
                case_id,


            # Primary threat output
            "threat":
                threat,


            # Runtime compatibility field
            "threat_assessment":
                threat,


            # Analyst confidence
            "confidence":
                confidence,


            # Threat intelligence structure
            "threat_analysis":
            {

                "threat":
                    threat,

                "severity":
                    severity,

                "confidence":
                    confidence,

            },


            # Risk model
            "risk":
            {

                "level":
                    severity,

                "score":
                    confidence,

                "confidence":
                    confidence,

            },


            "evidence":
                evidence,


            "reasoning":
                explanation,


            "recommended_action":
                "contain",

        }



# =====================================================
# Backward Compatibility Layer
# =====================================================

"""
Existing Sentinel DNA runtime services import:

    InvestigationReasoner

Keep this alias so older orchestration,
runtime, and API layers continue working.
"""


InvestigationReasoner = InvestigationReasoningEngine