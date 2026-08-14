from .models import DetectionRule
from .repository import DetectionRuleRepository
from .evaluator import DetectionEvaluator
from .rules import STARTER_RULES
class DetectionEngineeringService:
    def __init__(self,repository=None): self.repository=repository or DetectionRuleRepository(); [self.repository.create_rule(r) for r in STARTER_RULES if not self.repository.get_rule(r.id)]; self.evaluator=DetectionEvaluator(self.repository.list_rules()); self.detections=[]
    def create_detection_rule(self,**kwargs): return self.repository.create_rule(DetectionRule(**kwargs))
    def evaluate_security_event(self,event): result=self.evaluator.evaluate_event(event); self.detections.append(result); return result
    def get_detection_catalog(self): return [r.to_dict() for r in self.repository.list_rules()]
    def get_detection_metrics(self):
        return {"total_rules":len(self.repository.list_rules()),"active_rules":sum(r.status=="active" for r in self.repository.list_rules()),"detections_generated":sum(x.detection_count for x in self.detections),"highest_severity":max((x.highest_severity for x in self.detections),default="low"),"mitre_coverage":sorted({t for r in self.repository.list_rules() for t in r.mitre_techniques})}
