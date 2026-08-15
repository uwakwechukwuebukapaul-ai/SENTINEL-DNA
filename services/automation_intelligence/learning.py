class AutomationLearning:
    def summarize(self, experiences):
        return {"observations": len(experiences), "outcomes": sorted({x.outcome for x in experiences}), "feedback": [x.analyst_feedback for x in experiences if x.analyst_feedback]}
