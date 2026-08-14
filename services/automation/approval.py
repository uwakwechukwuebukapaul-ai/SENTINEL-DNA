from __future__ import annotations
from .models import APPROVAL_STATES, Execution

class ApprovalWorkflow:
    def set_state(self, execution: Execution, state: str) -> Execution:
        if state not in APPROVAL_STATES: raise ValueError("invalid_approval_state")
        if execution.approval != "pending": raise ValueError("approval_already_decided")
        execution.approval = state
        execution.status = "approved" if state == "approved" else "rejected"
        return execution
