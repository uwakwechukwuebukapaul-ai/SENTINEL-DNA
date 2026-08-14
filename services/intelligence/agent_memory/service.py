import hashlib
from .models import AgentExperience,AgentMessage,CollaborationContext
from .repository import AgentMemoryRepository
from .message_bus import AgentMessageBus
from .feedback import FeedbackTracker
class AgentMemoryService:
 def __init__(self,repository=None): self.repository=repository or AgentMemoryRepository(); self.bus=AgentMessageBus(); self.feedback=FeedbackTracker()
 def remember_experience(self,tenant_id,agent_id,case_id,task_type,outcome,confidence=0.): return self.repository.save_experience(AgentExperience("EXP-"+hashlib.sha256(f"{tenant_id}|{agent_id}|{case_id}|{task_type}".encode()).hexdigest()[:16],tenant_id,agent_id,case_id,task_type,outcome,confidence))
 def publish(self,tenant_id,sender,recipient,message_type,payload): return self.bus.publish(AgentMessage("MSG-"+hashlib.sha256(f"{tenant_id}|{sender}|{recipient}|{message_type}|{payload}".encode()).hexdigest()[:16],tenant_id,sender,recipient,message_type,payload))
 def collaboration_context(self,case_id,tenant_id,agents=None): return CollaborationContext(case_id,tenant_id,list(agents or []),self.bus.receive("broadcast",tenant_id))
 def confidence_metrics(self,tenant_id,agent_id=None):
  xs=self.repository.get_experiences(tenant_id,agent_id); return {"count":len(xs),"average_confidence":round(sum(x.get("confidence",0) for x in xs)/len(xs),4) if xs else 0.0}
