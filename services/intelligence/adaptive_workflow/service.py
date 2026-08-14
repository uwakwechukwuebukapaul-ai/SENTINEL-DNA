from .workflow_engine import AdaptiveWorkflowEngine
from .state_machine import InvestigationStateMachine
class AdaptiveWorkflowService:
 def __init__(self): self.engine=AdaptiveWorkflowEngine(); self.states=InvestigationStateMachine()
 def recommend(self,case_id,**signals): return self.engine.create(case_id,**signals)
 def transition(self,context,next_state): context.state=self.states.transition(context.state,next_state); return context
