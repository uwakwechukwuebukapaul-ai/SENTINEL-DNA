from .models import PreventionOutcome
class OutcomeTracker:
 def __init__(self,repository): self.repository=repository
 def record(self,org,action_id,result,effectiveness,lessons=""): x=PreventionOutcome(org,action_id,result,effectiveness,lessons); self.repository.outcomes.append(x); return x
