class CoverageEngine:
    def calculate(self,controls):
        return round(sum(bool(x.evidence_refs) for x in controls)/len(controls),2) if controls else 0.0
