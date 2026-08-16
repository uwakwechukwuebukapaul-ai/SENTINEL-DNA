from .models import InvestigationQuality,stable_id
class InvestigationQualityService:
 def __init__(self,platform=None):self.platform=platform
 def derive(self,t,c):
  base=self.platform.derive(t,c) if self.platform else {};r=base.get('intelligence',{});v=InvestigationQuality(t,c,stable_id(t,c,'investigation-quality'),r.get('evidence_completeness','insufficient_data'),'insufficient_data','available' if r.get('provenance') else 'insufficient_data',r.get('investigation_confidence','insufficient_data'),'insufficient_data');return {'tenant_id':t,'quality':v.to_dict(),'advisory_only':True}
