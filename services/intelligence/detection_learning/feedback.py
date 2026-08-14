import hashlib
from .models import DetectionFeedback
class FeedbackService:
 def create(self,tenant_id,detection_id,analyst_verdict,true_positive=False,false_positive=False,severity_adjustment="",tuning_notes=""):
  fid="DF-"+hashlib.sha256(f"{tenant_id}|{detection_id}|{analyst_verdict}|{tuning_notes}".encode()).hexdigest()[:16]; return DetectionFeedback(fid,detection_id,analyst_verdict,true_positive,false_positive,severity_adjustment,tuning_notes,tenant_id)
