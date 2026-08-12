from dataclasses import dataclass

from sentinel_dna.case_management.models import Case
from sentinel_dna.evidence.models import Evidence
from sentinel_dna.risk.risk_engine import RiskAssessment


@dataclass
class InvestigationSummary:
    case_id: str
    executive_summary: str
    key_findings: list[str]
    recommended_actions: list[str]
    confidence_statement: str


class InvestigationReporter:
    """Builds explainable investigation summaries and recommendations."""

    def summarize(
        self,
        case: Case,
        evidence_items: list[Evidence],
        risk_assessment: RiskAssessment,
        recommended_actions: list[str] | None = None,
    ) -> InvestigationSummary:
        key_findings = [
            (
                f"Case severity is {case.severity} and current "
                f"risk is {risk_assessment.level}."
            ),
            (
                f"{len(evidence_items)} evidence item(s) are "
                "attached to the investigation."
            ),
        ]

        for evidence in evidence_items:
            key_findings.append(
                f"{evidence.summary} with confidence {evidence.confidence}."
            )

        if recommended_actions is None:
            recommended_actions = self.recommend_actions(
                risk_assessment.level
            )

        return InvestigationSummary(
            case_id=case.case_id,
            executive_summary=(
                f"Sentinel DNA assessed '{case.title}' as "
                f"{risk_assessment.level} risk with "
                f"score {risk_assessment.score}/100."
            ),
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            confidence_statement=(
                "This summary is rules-assisted and explainable; "
                "analyst validation is required before decision."
            ),
        )

    def recommend_actions(self, level: str) -> list[str]:
        normalized_level = str(level).lower()

        if normalized_level in {"critical", "high"}:
            return [
                "Escalate to senior analyst.",
                (
                    "Preserve related email, endpoint, identity, "
                    "and network evidence."
                ),
                (
                    "Contain affected accounts or assets if "
                    "compromise is plausible."
                ),
            ]

        if normalized_level == "medium":
            return [
                (
                    "Request additional context from identity "
                    "and endpoint telemetry."
                ),
                "Monitor related indicators for recurrence.",
            ]

        return [
            "Document rationale and close or monitor if no additional evidence appears."
        ]

    def _actions_for_risk(self, level: str) -> list[str]:
        """Backward-compatible internal alias.

        New callers should use recommend_actions().
        """
        return self.recommend_actions(level)