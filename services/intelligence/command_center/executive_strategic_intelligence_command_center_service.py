from .governance_signal import stable_governance_signal_id
from .executive_strategic_intelligence_command_center import ExecutiveStrategicIntelligenceCommandCenter

class ExecutiveStrategicIntelligenceCommandCenterService:
    def __init__(self, portfolio, governance, intervention, learning, evolution, maturity, health, decision):
        self.sources = (portfolio, governance, intervention, learning, evolution, maturity, health, decision)
    def derive(self, tenant_id):
        values = []
        for source in self.sources:
            value = source.derive(tenant_id) if source else {}
            values.append(value if isinstance(value, dict) else {})
        portfolio, governance, intervention, learning, evolution, maturity, health, decision = values
        def section(value, *keys):
            for key in keys:
                if isinstance(value.get(key), dict): return value[key]
            return value
        p, g, i, l, e, m, h, d = (section(v, "portfolio", "summary", "governance", "intervention", "learning", "evolution", "maturity", "health", "profile") for v in values)
        uncertainty = tuple(sorted({u for v in values for u in (v.get("uncertainty", ()) or ())}))
        provenance = tuple(sorted({str(x) for v in values for x in (v.get("provenance", ()) or ())}))
        output = ExecutiveStrategicIntelligenceCommandCenter(tenant_id, stable_governance_signal_id(tenant_id, "executive-strategic-intelligence-command-center"), h.get("coverage_posture", "insufficient_history"), d.get("posture", "insufficient_history"), tuple(p.get("signals", p.get("portfolio_signals", ())) or ()), tuple(e.get("capability_signals", ()) or ()) + tuple(g.get("signals", ()) or ()) + tuple(i.get("signals", ()) or ()), m.get("posture", "insufficient_history"), g.get("posture", "insufficient_evidence"), e.get("convergence", e.get("posture", "insufficient_history")), m.get("trend", "insufficient_history"), tuple(h.get("missing_intelligence_areas", ()) or ()) + tuple(d.get("attention_areas", ()) or ()), h.get("confidence") or e.get("confidence"), h.get("evidence_strength", "insufficient_evidence"), uncertainty, provenance, True)
        return {"tenant_id": tenant_id, "command_center": output.to_dict(), "advisory_only": True}
    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["command_center"]
        return value if value["command_center_id"] == signal_id else None
