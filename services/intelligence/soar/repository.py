class SOARRepository:
    def __init__(self): self.playbooks={}; self.executions={}; self.approvals={}
    def create_playbook(self,p): self.playbooks[p.id]=p; return p
    def get_playbook(self,i): return self.playbooks.get(i)
    def list_playbooks(self): return list(self.playbooks.values())
    def save_execution(self,e): self.executions[e.execution_id]=e; return e
    def get_execution(self,i): return self.executions.get(i)
    def save_approval(self,a): self.approvals[a.approval_id]=a; return a
