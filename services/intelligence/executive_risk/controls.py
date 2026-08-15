class ControlAnalyzer:
    def assess(self,controls):
        total=len(controls); effective=sum(bool(x.get("effective")) for x in controls); return round(effective/total,2) if total else 0.0
