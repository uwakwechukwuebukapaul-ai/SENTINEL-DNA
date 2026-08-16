from .models import InvestigationMetrics,stable_id
class InvestigationMetricsService:
 def derive(self,t):
  v=InvestigationMetrics(t,stable_id(t,'metrics','investigation-lifecycle'),(), 'insufficient_history',(),('No lifecycle history is available.',),True);return {'tenant_id':t,'metrics':v.to_dict(),'advisory_only':True}
