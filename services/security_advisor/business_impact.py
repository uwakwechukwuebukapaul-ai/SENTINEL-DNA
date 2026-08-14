class BusinessImpactEngine:
 def assess(self,asset_criticality="MEDIUM",regulatory=False): return {"level":"HIGH" if asset_criticality.upper() in ("HIGH","CRITICAL") or regulatory else "MEDIUM","operational_impact":"Service disruption risk","regulatory_impact":"Review required" if regulatory else "Low"}
