class TwinRiskEngine:
 def calculate(self,asset,blast_radius=0,attack_paths=0):
  base={"LOW":20,"MEDIUM":45,"HIGH":70,"CRITICAL":90}.get(asset.criticality.upper(),45); score=min(100,base+min(10,blast_radius)+min(10,attack_paths*3)); return {"score":score,"severity":"CRITICAL" if score>=85 else "HIGH" if score>=65 else "MEDIUM" if score>=35 else "LOW","business_impact":"High business impact" if asset.criticality.upper() in ("HIGH","CRITICAL") else "Moderate business impact"}
