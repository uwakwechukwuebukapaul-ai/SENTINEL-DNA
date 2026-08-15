class OperationalForecaster:
    def forecast(self,snapshots):
        if len(snapshots)<2:return {"direction":"unknown","projected_pressure":None}
        current=sum(s.utilization for s in snapshots[-1:]); previous=sum(s.utilization for s in snapshots[:-1])/max(1,len(snapshots)-1); return {"direction":"increasing" if current>previous else "decreasing" if current<previous else "stable","projected_pressure":round(current+(current-previous),3)}
