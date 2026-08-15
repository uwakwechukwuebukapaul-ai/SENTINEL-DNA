class ExecutiveTrendAnalyzer:
    def direction(self,values):
        if len(values)<2:return "unknown"
        return "increasing" if values[-1]>values[0] else "decreasing" if values[-1]<values[0] else "stable"
