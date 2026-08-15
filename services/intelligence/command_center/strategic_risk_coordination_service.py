from .strategic_risk_coordination import StrategicRiskCoordination
from .governance_signal import stable_governance_signal_id
class StrategicRiskCoordinationService:
    def __init__(self,command_center=None,early_warning=None): self.command_center=command_center; self.early_warning=early_warning
    def derive(self,t):
        c=self.command_center.derive(t) if self.command_center else {}; x=c.get('command_center',{}); w=(self.early_warning.derive(t) if self.early_warning else {}).get('early_warning',{}); risks=tuple(x.get('strategic_risks',())); posture='insufficient_history' if x.get('governance_posture')=='insufficient_history' else 'related' if risks else 'isolated'; r=StrategicRiskCoordination(t,stable_governance_signal_id(t,'coordination'),posture,risks,(),risks,tuple(w.get('signals',())),tuple(x.get('governance_blockers',())),tuple(x.get('strategic_opportunities',())),('Co-occurring governance conditions require coordinated review.',) if risks else (),risks,tuple(x.get('uncertainty',())),x.get('confidence'),tuple(x.get('uncertainty',())),tuple(x.get('provenance',())),tuple(x.get('contributing_references',())),True); return {'tenant_id':t,'coordination':r.to_dict(),'advisory_only':True}
    def detail(self,t,i): x=self.derive(t)['coordination']; return x if x['coordination_id']==i else None
