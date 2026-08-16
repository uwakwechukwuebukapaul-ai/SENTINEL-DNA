from .governance_signal import stable_governance_signal_id
from .executive_intelligence_summary import ExecutiveIntelligenceSummary
class ExecutiveIntelligenceSummaryService:
    def __init__(self, improvement, evolution, maturity): self.sources = (improvement, evolution, maturity)
    def derive(self, tenant_id):
        vals = [(s.derive(tenant_id) if s else {}) for s in self.sources]
        payloads = [next((v[k] for k in ("continuous_improvement", "evolution", "maturity", "analytics", "command_center") if isinstance(v.get(k), dict)), v) for v in vals]
        opportunities = tuple(x for v in payloads for x in (v.get("opportunities", ()) or ()))
        risks = tuple(x for v in payloads for x in (v.get("risks", ()) or ()))
        reviews = tuple(x for v in payloads for x in (v.get("next_step_considerations", v.get("optimization_considerations", ())) or ()))
        posture = next((v.get("posture") or v.get("convergence") for v in payloads if v.get("posture") or v.get("convergence")), "insufficient_history")
        summary = "Executive intelligence reflects observed evidence and derived advisory interpretations; it does not make decisions or establish causation." if any(payloads) else "Insufficient history for an executive intelligence summary."
        value = ExecutiveIntelligenceSummary(tenant_id, stable_governance_signal_id(tenant_id, "executive-intelligence-summary"), summary, posture, opportunities, risks, reviews, tuple(sorted({u for v in payloads for u in (v.get("uncertainty", ()) or ())})), tuple(sorted({str(x) for v in payloads for x in (v.get("provenance", ()) or ())})), True)
        return {"tenant_id": tenant_id, "summary": value.to_dict(), "advisory_only": True}
    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["summary"]
        return value if value["summary_id"] == signal_id else None
