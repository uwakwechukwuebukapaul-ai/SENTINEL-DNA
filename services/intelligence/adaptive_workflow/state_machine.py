class InvestigationStateMachine:
 STATES=("CREATED","TRIAGING","INVESTIGATING","ANALYZING","VALIDATING","DECIDING","REPORTING","COMPLETED")
 def transition(self,current,next_state):
  if current not in self.STATES or next_state not in self.STATES or self.STATES.index(next_state)!=self.STATES.index(current)+1: raise ValueError("invalid_state_transition")
  return next_state
