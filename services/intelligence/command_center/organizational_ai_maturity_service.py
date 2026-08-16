from .governance_signal import stable_governance_signal_id
from .organizational_ai_maturity import OrganizationalAIMaturity
class OrganizationalAIMaturityService:
    def __init__(self, maturity, operating, governance, adoption): self.sources=(maturity,operating,governance,adoption)
    def derive(self,tenant_id):
        vals=[s.derive(tenant_id) if s else {} for s in self.sources]
        p=[next((v[k] for k in ("maturity","analytics","operating_model","governance","adoption") if isinstance(v.get(k),dict)),v) for v in vals]
        m,o,g,a=p
        stages=("emerging","developing","established","advanced")
        level=m.get("posture",m.get("maturity_level","emerging")); level=level if level in stages else "emerging"
        value=OrganizationalAIMaturity(tenant_id,stable_governance_signal_id(tenant_id,"organizational-ai-maturity"),level,m.get("posture","insufficient_history"),g.get("portfolio_oversight_posture",o.get("governance_readiness","insufficient_evidence")),a.get("usage_posture",o.get("intelligence_adoption_posture","insufficient_history")),m.get("evidence_strength","insufficient_evidence"),m.get("trend","insufficient_history"),tuple(sorted({u for v in p for u in (v.get("uncertainty",()) or ())})),tuple(sorted({str(x) for v in p for x in (v.get("provenance",()) or ())})),True)
        return {"tenant_id":tenant_id,"maturity":value.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        v=self.derive(tenant_id)["maturity"]; return v if v["maturity_id"]==signal_id else None
