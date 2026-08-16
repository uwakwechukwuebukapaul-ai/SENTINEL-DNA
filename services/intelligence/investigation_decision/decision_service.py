from .models import DecisionAnalysis,stable_id
from .decision_engine import DecisionIntelligenceEngine
class InvestigationDecisionService:
 def __init__(self,context_provider=None,engine=None):self.context_provider=context_provider;self.engine=engine or DecisionIntelligenceEngine()
 def derive(self,tenant_id,context=None):
  context=context or (self.context_provider(tenant_id) if self.context_provider else {});result=self.engine.analyze(context);v=DecisionAnalysis(tenant_id,stable_id(tenant_id,'investigation-decision-analysis'),'review_required' if context.get('evidence') else 'insufficient_evidence',result['confidence']['level'],tuple(result['confidence']['uncertainty']),(('observed_evidence_count',result['evidence_weighting']['observed_evidence_count']),),tuple(result['recommendations']['investigation_path_considerations']),tuple(context.get('provenance',())),True);return {'tenant_id':tenant_id,'analysis':v.to_dict(),'details':result,'advisory_only':True}
 def detail(self,tenant_id,analysis_id):
  value=self.derive(tenant_id);return value if value['analysis']['analysis_id']==analysis_id else None
