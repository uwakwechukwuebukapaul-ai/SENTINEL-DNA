from .risk_response_planning import RiskResponsePlanning
from .governance_signal import stable_governance_signal_id
class RiskResponsePlanningService:
    def __init__(self,coordination=None,priority=None): self.coordination=coordination; self.priority=priority
    def derive(self,t):
        c=(self.coordination.derive(t) if self.coordination else {}).get('coordination',{}); p=(self.priority.derive(t) if self.priority else {}).get('priority',{}); risks=tuple(c.get('converging_risks',())); x=RiskResponsePlanning(t,stable_governance_signal_id(t,'risk-response'),risks[0] if risks else None,p.get('priority','P4_INFORMATIONAL'),'Clarify governance conditions and validate evidence before strategic reliance.','Coordinate human review of co-occurring signals; no response is executed.','Additional observed outcomes, governance evidence, and decision context.',('Sufficient historical evidence and provenance.',),('Human approval and policy review.',),tuple(c.get('uncertainty',())),c.get('confidence'),tuple(c.get('provenance',())),True); return {'tenant_id':t,'planning':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['planning']; return x if x['planning_id']==s else None
