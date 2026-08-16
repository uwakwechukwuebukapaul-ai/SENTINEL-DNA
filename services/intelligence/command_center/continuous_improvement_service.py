from .continuous_improvement import ContinuousImprovement
from .governance_signal import stable_governance_signal_id


class ContinuousImprovementService:
    def __init__(self, portfolio, strategy, learning):
        self.portfolio, self.strategy, self.learning = portfolio, strategy, learning

    def derive(self, tenant_id):
        portfolio = (self.portfolio.derive(tenant_id) if self.portfolio else {}).get("portfolio", {})
        strategy = (self.strategy.derive(tenant_id) if self.strategy else {}).get("analytics", {})
        learning = (self.learning.derive(tenant_id) if self.learning else {}).get("learning", {})
        opportunities = tuple(strategy.get("improvement_opportunities", ())) or tuple(portfolio.get("learning_opportunities", ()))
        value = ContinuousImprovement(
            tenant_id, stable_governance_signal_id(tenant_id, "continuous-improvement"), opportunities,
            tuple(learning.get("lessons_learned", ())), tuple(strategy.get("effectiveness_patterns", ())),
            strategy.get("strategy_posture", "insufficient_evidence"),
            ("Review evidence coverage before selecting an improvement action.",) if not opportunities else (),
            strategy.get("governance_maturity_alignment", "insufficient_evidence"), strategy.get("confidence"),
            tuple(sorted(set(portfolio.get("uncertainty", ())) | set(strategy.get("uncertainty", ())) | set(learning.get("uncertainty", ())))),
            tuple(sorted(set(portfolio.get("provenance", ())) | set(strategy.get("provenance", ())) | set(learning.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "continuous_improvement": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["continuous_improvement"]
        return value if value["improvement_id"] == signal_id else None
