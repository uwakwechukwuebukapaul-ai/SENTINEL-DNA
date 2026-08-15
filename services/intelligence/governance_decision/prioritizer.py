class DecisionPrioritizer:
    weights={"critical":4,"high":3,"medium":2,"low":1}
    def score(self,signal): return self.weights.get(signal.severity,2)+self.weights.get(signal.direction if signal.direction in self.weights else "medium",2)+(1 if signal.affected_assets else 0)+(1 if signal.affected_controls else 0)
    def priority(self,signal):
        score=self.score(signal); return "critical" if score>=8 else "high" if score>=6 else "medium" if score>=4 else "low"
