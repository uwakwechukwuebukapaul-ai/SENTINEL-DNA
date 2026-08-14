from .registry import AgentRegistry
from .workflow import AgentWorkflowEngine
from .approval import ApprovalManager
from .audit import AgentAuditLogger
class AgentOrchestrationService:
 def __init__(self,registry=None): self.registry=registry or AgentRegistry(); self.workflow=AgentWorkflowEngine(self.registry); self.approval=ApprovalManager(); self.audit=AgentAuditLogger()
 def register(self,agent): self.audit.record("agent_registered",agent.agent_id); return self.registry.register_agent(agent)
 def execute(self,case_id,context,capabilities=None): return self.workflow.execute(case_id,context,capabilities or ["evidence","threat_intel","reasoning","reporting"])
