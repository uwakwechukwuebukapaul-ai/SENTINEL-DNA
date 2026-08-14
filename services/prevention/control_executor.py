class ControlExecutor:
 def execute(self,action): action.execution_status="EXECUTED"; return {"action":action.public(),"requires_approval":action.approval_required}
