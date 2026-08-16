from .models import EvidenceReasoning,stable_id
class EvidenceReasoningService:
 def __init__(self,context=None,data_fabric=None):self.context,self.data_fabric=context,data_fabric
 def derive(self,t,c):
  ctx=self.context.get(t,c) if self.context and hasattr(self.context,'get') else {};q=self.data_fabric.report(t) if self.data_fabric else None;v=EvidenceReasoning(t,c,stable_id(t,c,'evidence-reasoning'),(('context_available',bool(ctx)),),tuple(ctx.get('indicators',())) if isinstance(ctx,dict) else (),('additional evidence review required',) if not ctx else (),getattr(q,'completeness','insufficient_data') if q else 'insufficient_data',('attribution and intent remain uncertain',),getattr(q,'provenance',()) if q else (),True);return {'tenant_id':t,'reasoning':v.to_dict(),'advisory_only':True}
