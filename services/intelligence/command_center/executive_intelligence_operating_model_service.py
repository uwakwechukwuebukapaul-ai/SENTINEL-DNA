from .governance_signal import stable_governance_signal_id
from .executive_intelligence_operating_model import ExecutiveIntelligenceOperatingModel
class ExecutiveIntelligenceOperatingModelService:
    def __init__(self, command_center, decision, health, summary, evolution, maturity): self.sources=(command_center,decision,health,summary,evolution,maturity)
    def derive(self, tenant_id):
        vals=[s.derive(tenant_id) if s else {} for s in self.sources]
        payload=[next((v[k] for k in ("command_center","profile","health","summary","evolution","maturity") if isinstance(v.get(k),dict)),v) for v in vals]
        cc,d,h,s,e,m=payload
        value=ExecutiveIntelligenceOperatingModel(tenant_id,stable_governance_signal_id(tenant_id,"executive-intelligence-operating-model"),cc.get("organizational_intelligence_posture",d.get("posture","insufficient_history")),"visible" if any(payload) else "insufficient_history","executive ownership with human review; no autonomous action",e.get("review_cadence","insufficient_history"),cc.get("governance_posture","insufficient_evidence"),s.get("adoption_posture", "insufficient_history"),h.get("evidence_strength","insufficient_evidence"),h.get("confidence") or e.get("confidence"),tuple(sorted({u for v in payload for u in (v.get("uncertainty",()) or ())})),tuple(sorted({str(x) for v in payload for x in (v.get("provenance",()) or ())})),True)
        return {"tenant_id":tenant_id,"operating_model":value.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        v=self.derive(tenant_id)["operating_model"]; return v if v["operating_model_id"]==signal_id else None
