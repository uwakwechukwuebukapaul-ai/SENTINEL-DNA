from .governance_signal import stable_governance_signal_id
from .organizational_decision_intelligence import OrganizationalDecisionIntelligence
class OrganizationalDecisionIntelligenceService:
    def __init__(self, readiness, strategy, maturity, health): self.readiness, self.strategy, self.maturity, self.health = readiness, strategy, maturity, health
    def derive(self, tenant_id):
        vals = [(s.derive(tenant_id) if s else {}) for s in (self.readiness, self.strategy, self.maturity, self.health)]
        readiness, strategy, maturity, health = vals
        def payload(v):
            for key in ("readiness", "strategy", "maturity", "health", "analytics", "profile"):
                if isinstance(v.get(key), dict): return v[key]
            return v
        r, s, m, h = map(payload, vals)
        value = OrganizationalDecisionIntelligence(tenant_id, stable_governance_signal_id(tenant_id, "organizational-decision-intelligence"), r.get("posture", s.get("posture", "insufficient_history")), tuple(r.get("signals", r.get("decision_readiness_signals", ())) or ()), tuple(s.get("signals", s.get("strategic_signals", ())) or ()), tuple(m.get("capability_signals", ()) or ()), tuple(m.get("governance_indicators", ()) or ()), h.get("coverage_posture", "insufficient_history"), tuple(sorted({u for v in vals for u in (v.get("uncertainty", ()) or ())})), tuple(sorted({str(x) for v in vals for x in (v.get("provenance", ()) or ())})), True)
        return {"tenant_id": tenant_id, "profile": value.to_dict(), "advisory_only": True}
    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["profile"]
        return value if value["profile_id"] == signal_id else None
