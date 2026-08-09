"""
Investigation Metrics

Defines measurable investigation
quality indicators.
"""


from dataclasses import dataclass


@dataclass
class InvestigationMetrics:

    evidence_found: int = 0

    expected_evidence: int = 0

    correct_findings: int = 0

    total_findings: int = 0

    response_actions: int = 0


    def evidence_coverage(self):

        if self.expected_evidence == 0:
            return 0

        return round(
            (
                self.evidence_found /
                self.expected_evidence
            ) * 100,
            2
        )


    def finding_accuracy(self):

        if self.total_findings == 0:
            return 0

        return round(
            (
                self.correct_findings /
                self.total_findings
            ) * 100,
            2
        )