from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
@dataclass
class DetectionFeedback:
 feedback_id:str; detection_id:str; analyst_verdict:str; true_positive:bool; false_positive:bool; severity_adjustment:str=""; tuning_notes:str=""; tenant_id:str="default"; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
 def to_dict(self): return asdict(self)
