from datetime import datetime,timezone
from .models import ControlAssessment
class ComplianceEvaluator:
 def evaluate_control(self,tenant_id,control,capabilities=None):
  caps=set(capabilities or []); status="implemented" if any(x in caps for x in control.requirements) else "unknown"; return ControlAssessment(f"ASM-{tenant_id}-{control.control_id}",tenant_id,control.control_id,status,1.0 if status=="implemented" else 0.0,[],datetime.now(timezone.utc).isoformat())
 def evaluate_framework(self,tenant_id,controls,capabilities=None): return [self.evaluate_control(tenant_id,c,capabilities) for c in controls]
 def generate_gap_report(self,assessments): return [a.control_id for a in assessments if a.status in {"missing","unknown"}]
