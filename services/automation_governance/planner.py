class AutomationPlanner:
    def plan(self, workflow, actions):
        for action in actions:
            if action.workflow_id != workflow.workflow_id: raise ValueError("action_workflow_mismatch")
        return list(actions)
