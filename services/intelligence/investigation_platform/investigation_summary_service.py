from .models import InvestigationSummary,stable_id
class InvestigationSummaryService:
 def __init__(self,intelligence=None,evidence=None):self.intelligence,self.evidence=intelligence,evidence
 def derive(self,t,c):
  v=InvestigationSummary(t,c,stable_id(t,c,'investigation-summary'),'Evidence-backed review is available only within the recorded context.','Analyst review remains required for interpretation.','Evidence completeness and provenance should be reviewed.','Uncertainty remains around attribution, intent, and causal conclusions.',('Review evidence and validate context with the case owner.',),(),True);return {'tenant_id':t,'summary':v.to_dict(),'advisory_only':True}
