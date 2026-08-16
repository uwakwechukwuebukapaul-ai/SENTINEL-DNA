from .ids import stable_id
from .models import HuntEffectiveness
class HuntEffectivenessService:
 def __init__(self,repository=None):self.repository=repository
 def derive(self,t):
  history=self.repository.history() if self.repository and hasattr(self.repository,'history') else ();v=HuntEffectiveness(t,stable_id(t,'hunt-effectiveness'),(('observed_hunt_count',len(history)),) if history else (),('outcomes observed alongside hunt history',) if history else (), 'associated temporal interpretation' if history else 'insufficient_history',('effectiveness is associated with observed history; causation is not established',) if history else ('effectiveness history is empty',),(),True)
  return {'tenant_id':t,'effectiveness':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['effectiveness'];return v if v['effectiveness_id']==i else None
