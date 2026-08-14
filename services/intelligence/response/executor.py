from uuid import uuid4
from .models import ExecutionResult

class SimulationExecutor:
    def execute(self, plan, approval):
        if approval is None or approval.decision != "approved": return ExecutionResult(str(uuid4()), plan.plan_id, plan.tenant_id, "blocked", message="Approval required before execution")
        return ExecutionResult(str(uuid4()), plan.plan_id, plan.tenant_id, "simulated", actions=[{"action_id": action.action_id, "status": "simulated"} for action in plan.actions])
