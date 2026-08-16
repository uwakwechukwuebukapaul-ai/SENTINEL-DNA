from .models import ThreatAssessment,stable_id
class ThreatAssessmentService:
 def __init__(self,detection=None,hunting=None,ioc=None,classification=None):self.sources=(detection,hunting,ioc,classification)
 def derive(self,t,c):
  vals=[s.derive(t) if s and hasattr(s,'derive') else {} for s in self.sources];v=ThreatAssessment(t,c,stable_id(t,c,'threat-assessment'),'review_required' if any(vals) else 'insufficient_data','advisory severity interpretation','moderate' if any(vals) else 'insufficient_data',('available intelligence is incomplete',) if not any(vals) else ('threat posture is an advisory interpretation',),(),True);return {'tenant_id':t,'assessment':v.to_dict(),'advisory_only':True}
