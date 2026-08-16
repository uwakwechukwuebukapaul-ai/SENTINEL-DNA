from .governance_signal import stable_governance_signal_id
from .intelligence_feedback_loop import IntelligenceFeedbackLoop
class IntelligenceFeedbackLoopService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("adoption","summary","analytics","continuous_improvement") if isinstance(v.get(k),dict)),v) for v in vals]
        v=IntelligenceFeedbackLoop(t,stable_governance_signal_id(t,"intelligence-feedback-loop"),tuple(x for q in p for x in (q.get("usefulness_signals",()) or ())),tuple(x for q in p for x in (q.get("improvement_opportunities",q.get("enablement_opportunities",())) or ())),tuple(x for q in p for x in (q.get("governance_learning_inputs",()) or ())),tuple(x for q in p for x in (q.get("maturity_refinement_areas",q.get("maturity_gaps",())) or ())),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"feedback":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["feedback"]; return v if v["feedback_id"]==i else None
