from .models import InvestigationProgress,stable_id
class InvestigationProgressService:
 def derive(self,t,c):
  v=InvestigationProgress(t,c,stable_id(t,c,'investigation-progress'),('intake observed',),('evidence review',),('supporting evidence requires validation',),('analyst review required',),'insufficient_data');return {'tenant_id':t,'progress':v.to_dict(),'advisory_only':True}
