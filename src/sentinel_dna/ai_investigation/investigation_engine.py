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


class InvestigationEngine:
    def summarize(
        self,
        case: Case,
        evidence_items: list[Evidence],
        risk_assessment: RiskAssessment,
    ) -> InvestigationSummary:
        key_findings = [
            f"Case severity is {case.severity} and current risk is {risk_assessment.level}.",
            f"{len(evidence_items)} evidence item(s) are attached to the investigation.",
        ]
        for evidence in evidence_items:
            key_findings.append(f"{evidence.summary} with confidence {evidence.confidence}.")
        recommended_actions = self._actions_for_risk(risk_assessment.level)
        return InvestigationSummary(
            case_id=case.case_id,
            executive_summary=(
                f"Sentinel DNA assessed '{case.title}' as {risk_assessment.level} risk "
                f"with score {risk_assessment.score}/100."
            ),
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            confidence_statement="This summary is rules-assisted and explainable; analyst validation is required before decision.",
        )

    def _actions_for_risk(self, level: str) -> list[str]:
        if level in {"critical", "high"}:
            return [
                "Escalate to senior analyst.",
                "Preserve related email, endpoint, identity, and network evidence.",
                "Contain affected accounts or assets if compromise is plausible.",
            ]
        if level == "medium":
            return [
                "Request additional context from identity and endpoint telemetry.",
                "Monitor related indicators for recurrence.",
            ]
        return ["Document rationale and close or monitor if no additional evidence appears."]

