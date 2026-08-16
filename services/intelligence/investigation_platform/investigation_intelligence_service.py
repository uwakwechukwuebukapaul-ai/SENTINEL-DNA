from .models import InvestigationIntelligence,stable_id
class InvestigationIntelligenceService:
 def __init__(self,evidence=None,threat=None,plan=None):self.evidence,self.threat,self.plan=evidence,threat,plan
 def derive(self,t,c):
  e=self.evidence.derive(t,c) if self.evidence else {};a=self.threat.derive(t,c) if self.threat else {};p=self.plan.derive(t,c) if self.plan else {};v=InvestigationIntelligence(t,c,stable_id(t,c,'investigation-intelligence'),a.get('assessment',{}).get('threat_posture','insufficient_data'),a.get('assessment',{}).get('confidence','insufficient_data'),e.get('reasoning',{}).get('evidence_quality_interpretation','insufficient_data'),'Observed signals suggest analyst review; no causal conclusion is established.',tuple(p.get('plan',{}).get('recommended_investigation_steps',())),tuple(e.get('reasoning',{}).get('provenance',())),tuple(e.get('reasoning',{}).get('supporting_indicators',())),True);return {'tenant_id':t,'intelligence':v.to_dict(),'advisory_only':True}
