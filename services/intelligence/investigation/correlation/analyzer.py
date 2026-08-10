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


        for evidence in evidence_items:

            value = str(
                evidence.value
            ).lower()


            if any(
                term in value
                for term in self.SUSPICIOUS_TERMS
            ):

                finding = CorrelationFinding(
                    category="suspicious_indicator",
                    value=evidence.value,
                    risk="high",
                    confidence=85,
                    metadata={
                        "source":
                            evidence.source,
                        "evidence_type":
                            evidence.evidence_type,
                    },
                )

                result.add(
                    finding
                )


            else:

                finding = CorrelationFinding(
                    category="observed_artifact",
                    value=evidence.value,
                    risk="low",
                    confidence=50,
                    metadata={
                        "source":
                            evidence.source,
                    },
                )

                result.add(
                    finding
                )


        return result