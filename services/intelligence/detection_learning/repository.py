class DetectionLearningRepository:
 def __init__(self): self.feedback={}
 def save_feedback(self,x): self.feedback[x.feedback_id]=x; return x
 def list_feedback(self,tenant_id=None,detection_id=None): return [x for x in self.feedback.values() if (tenant_id is None or x.tenant_id==tenant_id) and (detection_id is None or x.detection_id==detection_id)]
