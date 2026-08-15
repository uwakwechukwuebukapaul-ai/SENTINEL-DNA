class OptimizationPrioritizer:
    def score(self,x): return round(min(10.0,(x.frequency if x.frequency else 0)+(2 if x.impact in {"high","critical"} else 0)+(1 if x.evidence_quality=="HIGH" else 0)),2)
    def priority(self,x):
        s=self.score(x); return "high" if s>=6 else "medium" if s>=3 else "low"
