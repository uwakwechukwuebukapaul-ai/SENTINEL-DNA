from .governance_signal import stable_governance_signal_id
from .strategic_intelligence_health import StrategicIntelligenceHealth
class StrategicIntelligenceHealthService:
    def __init__(self, *sources): self.sources = sources
    def derive(self, tenant_id):
        vals = [(s.derive(tenant_id) if s else {}) for s in self.sources]
        payloads = [next((v[k] for k in ("portfolio", "analytics", "maturity", "evolution", "health") if isinstance(v.get(k), dict)), v) for v in vals]
        evidence = [v.get("evidence_strength", "insufficient_evidence") for v in payloads]
        known = sum(x != "insufficient_evidence" for x in evidence)
        posture = "insufficient_history" if not vals or known == 0 else "covered" if known == len(evidence) else "partial_coverage"
        value = StrategicIntelligenceHealth(tenant_id, stable_governance_signal_id(tenant_id, "strategic-intelligence-health"), round(known / len(evidence) * 100) if evidence else None, posture, tuple(sorted(set(str(v.get("confidence")) for v in payloads if v.get("confidence") is not None))), "insufficient_evidence" if not known else ("strong" if all(x in ("strong", "high") for x in evidence if x != "insufficient_evidence") else "mixed"), tuple(sorted({u for v in payloads for u in (v.get("uncertainty", ()) or ())})), ("portfolio", "governance", "intervention", "learning", "evolution", "maturity") if not known else (), (), min(evidence, key=lambda x: (x == "insufficient_evidence", x)) if evidence else "insufficient_evidence", tuple(sorted({str(x) for v in payloads for x in (v.get("provenance", ()) or ())})), True)
        return {"tenant_id": tenant_id, "health": value.to_dict(), "advisory_only": True}
    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["health"]
        return value if value["health_id"] == signal_id else None
