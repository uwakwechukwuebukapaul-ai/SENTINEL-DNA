class IncidentStateMachine:
    STATES = ("NEW", "TRIAGED", "INVESTIGATING", "CONTAINING", "ERADICATING", "RECOVERING", "RESOLVED", "CLOSED")
    def can_transition(self, previous, new): return new in self.STATES and self.STATES.index(new) == self.STATES.index(previous) + 1
