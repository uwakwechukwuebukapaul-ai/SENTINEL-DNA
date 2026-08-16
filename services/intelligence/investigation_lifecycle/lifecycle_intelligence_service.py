from .models import LifecycleIntelligence,stable_id
class LifecycleIntelligenceService:
 def __init__(self,platform=None):self.platform=platform
 def derive(self,t,c):
  base=self.platform.derive(t,c) if self.platform else {};v=LifecycleIntelligence(t,c,stable_id(t,c,'lifecycle-intelligence'),'intake',base.get('intelligence',{}).get('investigation_posture','insufficient_history'),(),base.get('intelligence',{}).get('evidence_completeness','insufficient_data'),('lifecycle history is insufficient',),tuple(base.get('intelligence',{}).get('provenance',())),base.get('intelligence',{}).get('investigation_confidence','insufficient_data'),True);return {'tenant_id':t,'lifecycle':v.to_dict(),'advisory_only':True}
