from .models import PreventionRecommendation
from .risk_predictor import RiskPredictor
from .action_planner import ActionPlanner
class PreventionEngine:
 def __init__(self,repository): self.repository=repository; self.predictor=RiskPredictor(); self.planner=ActionPlanner()
 def analyze(self,org,data):
  risk=self.predictor.predict(data.get("asset_criticality","MEDIUM"),data.get("blast_radius",0),data.get("attack_paths",0),data.get("threat_confidence",0),data.get("entity_risk",0)); actions=self.planner.plan(org,data.get("asset_id",""),data.get("threat_description","Threat detected"),risk["score"]); self.repository.actions.extend(actions); x=PreventionRecommendation(org,data.get("incident_id",""),data.get("asset_id",""),risk["score"],data.get("threat_description","Threat detected"),[a.public() for a in actions],risk["score"]/100,"PENDING_APPROVAL"); self.repository.recommendations.append(x); return x
