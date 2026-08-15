class AutomationSimulator:
    def run(self, action): return {"simulated": True, "action_type": action.action_type, "target_system": action.target_system, "external_change": False}
