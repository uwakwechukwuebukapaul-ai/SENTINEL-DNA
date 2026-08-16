from .ids import stable_id
from .models import HuntPrioritization
class HuntPrioritizationService:
 def __init__(self,intelligence=None):self.intelligence=intelligence
 def derive(self,t):
  base=self.intelligence.derive(t) if self.intelligence else {}; available=base.get('intelligence',{}).get('available_hunting_coverage')=='available'
  v=HuntPrioritization(t,stable_id(t,'hunt-prioritization'),'review' if available else 'insufficient_data',('available hunting history',) if available else (), 'moderate' if available else 'insufficient_data',('advisory prioritization based on observed evidence',),True)
  return {'tenant_id':t,'prioritization':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['prioritization'];return v if v['prioritization_id']==i else None
