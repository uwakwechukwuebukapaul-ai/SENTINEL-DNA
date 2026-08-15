from .governance_signal import stable_governance_signal_id
from .improvement_command_center import ImprovementCommandCenter


class ImprovementCommandCenterService:
    def __init__(self, portfolio, learning, trends):
        self.portfolio, self.learning, self.trends = portfolio, learning, trends

    def derive(self, tenant_id):
        portfolio = (self.portfolio.derive(tenant_id) if self.portfolio else {}).get("portfolio", {})
        learning = (self.learning.derive(tenant_id) if self.learning else {}).get("learning", {})
        trends = (self.trends.derive(tenant_id) if self.trends else {}).get("analytics", {})
        themes = tuple(portfolio.get("strategic_focus_areas", ()))
        posture = portfolio.get("posture", "insufficient_history")
        uncertainty = tuple(sorted(set(portfolio.get("uncertainty", ())) | set(trends.get("uncertainty", ()))))
        provenance = tuple(sorted(set(portfolio.get("provenance", ())) | set(trends.get("provenance", ()))))
        result = ImprovementCommandCenter(
            tenant_id, stable_governance_signal_id(tenant_id, "improvement-command-center"), posture,
            tuple(portfolio.get("learning_opportunities", ())) or tuple(portfolio.get("effectiveness_patterns", ())),
            posture,
            "Observed improvement themes are available for executive review." if themes else "Insufficient history for trend interpretation.",
            tuple(themes or learning.get("lessons_learned", ())),
            portfolio.get("evidence_strength") or trends.get("evidence_strength", "insufficient_evidence"),
            portfolio.get("confidence") or trends.get("confidence"), uncertainty, provenance, True,
        )
        return {"tenant_id": tenant_id, "command_center": result.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["command_center"]
        return value if value["command_center_id"] == signal_id else None
