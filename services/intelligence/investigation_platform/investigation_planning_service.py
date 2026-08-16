from .models import InvestigationPlanning,stable_id
class InvestigationPlanningService:
 def derive(self,t,c):
  v=InvestigationPlanning(t,c,stable_id(t,c,'investigation-plan'),('Review available evidence with the case owner.',),('Validate telemetry provenance and completeness.',),('What evidence supports the current assessment?',),('Compare observed signals with context.',),True);return {'tenant_id':t,'plan':v.to_dict(),'advisory_only':True}
