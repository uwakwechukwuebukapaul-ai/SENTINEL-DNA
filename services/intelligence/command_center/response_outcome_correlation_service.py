from .response_outcome_correlation import ResponseOutcomeCorrelation
from .governance_signal import stable_governance_signal_id
class ResponseOutcomeCorrelationService:
    def __init__(self,correlation=None,learning=None): self.correlation=correlation; self.learning=learning
    def derive(self,t):
        c=(self.correlation.derive(t) if self.correlation else {}).get('correlation',{}); l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); a=ResponseOutcomeCorrelation(t,stable_governance_signal_id(t,'response-outcome-correlation'),c.get('posture','insufficient_history'),tuple(c.get('correlation_candidates',())),c.get('relationship_strength','unavailable'),c.get('evidence_availability','insufficient_outcomes'),'Observed relationship or temporal association only; no causality is established.',c.get('confidence'),tuple(sorted(set(c.get('uncertainty',()))|set(l.get('uncertainty',())))),tuple(sorted(set(c.get('provenance',()))|set(l.get('provenance',())))),True); return {'tenant_id':t,'correlation':a.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['correlation']; return x if x['correlation_id']==s else None
