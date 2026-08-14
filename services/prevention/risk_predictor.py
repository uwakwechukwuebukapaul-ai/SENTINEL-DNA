class RiskPredictor:
 def predict(self,asset_criticality="MEDIUM",blast_radius=0,attack_paths=0,threat_confidence=0,entity_risk=0):
  base={"LOW":20,"MEDIUM":45,"HIGH":70,"CRITICAL":90}.get(asset_criticality.upper(),45); score=min(100,base+min(10,blast_radius)+min(10,attack_paths*3)+threat_confidence*10+entity_risk*.2); return {"score":round(score,2),"severity":"CRITICAL" if score>=85 else "HIGH" if score>=65 else "MEDIUM" if score>=35 else "LOW","explanation":"Risk combines asset criticality, blast radius, attack paths, threat confidence, and entity risk."}
