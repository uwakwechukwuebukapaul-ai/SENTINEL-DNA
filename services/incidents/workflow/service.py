from .models import IncidentWorkflow, now
from .state_machine import IncidentStateMachine
class WorkflowService:
    def __init__(self): self.items = {}; self.machine = IncidentStateMachine()
    def create(self, incident_id, organization_id):
        item = IncidentWorkflow(incident_id, organization_id); item.timestamps["NEW"] = now(); self.items[incident_id] = item; return item
    def transition(self, incident_id, organization_id, new_state, user_id, reason=""):
        item = self.items.get(incident_id)
        if not item or item.organization_id != organization_id: raise LookupError("incident_not_found")
        if not self.machine.can_transition(item.state, new_state): raise ValueError("invalid_state_transition")
        previous = item.state; item.state = new_state; item.timestamps[new_state] = now(); item.history.append({"previous_state": previous, "new_state": new_state, "user_id": user_id, "timestamp": item.timestamps[new_state], "reason": reason}); return item
    def get(self, incident_id, organization_id):
        item = self.items.get(incident_id)
        if not item or item.organization_id != organization_id: raise LookupError("incident_not_found")
        return item
