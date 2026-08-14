class AgentRegistry:
 def __init__(self): self.agents={}
 def register_agent(self,a): self.agents[a.agent_id]=a; return a
 def discover_agents(self,capability,tenant_id="default"): return [a for a in self.agents.values() if a.tenant_id==tenant_id and a.status=="available" and capability in a.capabilities]
 def enable(self,i): self.agents[i].status="available"; return self.agents[i]
 def disable(self,i): self.agents[i].status="disabled"; return self.agents[i]
 def get_capabilities(self): return {i:a.capabilities for i,a in self.agents.items()}
