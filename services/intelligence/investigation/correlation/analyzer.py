"""
Sentinel DNA Evidence Correlation Analyzer.

Transforms evidence into intelligence findings.
"""

from .models import (
    CorrelationFinding,
    IntelligenceResult,
)


class EvidenceCorrelationAnalyzer:
    """
    Analyzes investigation evidence.
    """

    SUSPICIOUS_TERMS = [
        "malicious",
        "phish",
        "evil",
        ".xyz",
        ".top",
        ".click",
    ]


    def analyze(
        self,
        evidence_items,
    ):

        result = IntelligenceResult()


        # Normalize dictionary input
        if isinstance(
            evidence_items,
            dict,
        ):
            evidence_items = list(
                evidence_items.values()
            )


        for evidence in evidence_items:

            if hasattr(
                evidence,
                "value",
            ):

                value = str(
                    evidence.value
                )

                source = (
                    evidence.source
                )

                evidence_type = (
                    evidence.evidence_type
                )

            else:

                value = str(
                    evidence
                )

                source = (
                    "pipeline_input"
                )

                evidence_type = (
                    "unknown"
                )


            normalized_value = (
                value.lower()
            )


            suspicious = any(
                term in normalized_value
                for term in self.SUSPICIOUS_TERMS
            )


            finding = CorrelationFinding(
                category=(
                    "suspicious_indicator"
                    if suspicious
                    else
                    "observed_artifact"
                ),

                value=value,

                risk=(
                    "high"
                    if suspicious
                    else
                    "low"
                ),

                confidence=(
                    85
                    if suspicious
                    else
                    50
                ),

                metadata={
                    "source": source,
                    "evidence_type": evidence_type,
                },
            )


            result.add(
                finding
            )


        return result