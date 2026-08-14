from .repository import SOARRepository
from .playbooks import STARTER_PLAYBOOKS
from .planner import SOARPlanner
from .approval import ApprovalEngine
from .executor import SOARExecutor
from .audit import SOARAuditLogger
class SOARService:
    def __init__(self,repository=None):
        self.repository=repository or SOARRepository(); [self.repository.create_playbook(p) for p in STARTER_PLAYBOOKS]; self.planner=SOARPlanner(); self.approval=ApprovalEngine(self.repository); self.executor=SOARExecutor(); self.audit=SOARAuditLogger()
    def create_playbook(self,p): return self.repository.create_playbook(p)
    def suggest_automation(self,result): return self.planner.generate_plan(result)
    def request_execution(self,playbook_id,case_id):
        e=self.repository.save_execution(self.executor.execute(self.repository.get_playbook(playbook_id),case_id,None)); self.approval.request_approval(e.execution_id); self.audit.record("execution_requested",execution_id=e.execution_id); return e
    def approve_execution(self,eid,who): return self.approval.approve(eid,who)
    def execute_playbook(self,pid,cid):
        approval=self.approval.get_status("EXE-"+pid+"-"+cid); e=self.repository.save_execution(self.executor.execute(self.repository.get_playbook(pid),cid,approval)); self.audit.record("playbook_executed",execution_id=e.execution_id,status=e.status); return e
    def get_execution_history(self): return list(self.repository.executions.values())
