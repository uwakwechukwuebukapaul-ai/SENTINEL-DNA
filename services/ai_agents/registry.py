class AgentRegistry:
    def __init__(self): self.agents=[]
    def add(self, agent): self.agents.append(agent); return agent
    def scoped(self, org): return [a for a in self.agents if a.organization_id==org]
