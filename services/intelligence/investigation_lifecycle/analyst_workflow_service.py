from .models import AnalystWorkflow,stable_id
class AnalystWorkflowService:
 def derive(self,t,c):
  v=AnalystWorkflow(t,c,stable_id(t,c,'analyst-workflow'),('Workflow state is observed from available context.',),('evidence context may be incomplete',),('Review provenance and evidence completeness with the case owner.',),True);return {'tenant_id':t,'workflow':v.to_dict(),'advisory_only':True}
