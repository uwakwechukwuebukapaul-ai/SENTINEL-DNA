from datetime import datetime, timezone
from .models import SOARExecution
class SOARExecutor:
    BLOCKED={"isolate endpoint","disable account","delete","external modification"}
    def execute(self,playbook,case_id,approval):
        eid="EXE-"+playbook.id+"-"+case_id; now=datetime.now(timezone.utc).isoformat()
        if approval is None or approval.status!="approved": return SOARExecution(eid,playbook.id,case_id,"blocked",[],now,now,{"reason":"approval_required","synthetic_only":True})
        safe=[a.action_type for a in playbook.actions if a.action_type not in self.BLOCKED]; return SOARExecution(eid,playbook.id,case_id,"completed",safe,now,datetime.now(timezone.utc).isoformat(),{"synthetic_only":True})
