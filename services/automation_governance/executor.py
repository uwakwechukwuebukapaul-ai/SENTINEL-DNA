class AutomationExecutor:
    def __init__(self, simulator=None):
        from .simulator import AutomationSimulator
        self.simulator=simulator or AutomationSimulator()
    def execute(self, actions): return [self.simulator.run(action) for action in actions]
