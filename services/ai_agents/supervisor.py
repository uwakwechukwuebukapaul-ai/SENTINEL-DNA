class AgentSupervisor:
    def __init__(self, registry, memory): self.registry=registry; self.memory=memory
    def run(self, organization_id, alert):
        agents=self.registry.scoped(organization_id); results=[]
        for agent in agents:
            agent.status="COMPLETED"; agent.last_execution=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(); agent.confidence=.8; results.append({"agent":agent.agent_type,"recommendation":"Review alert evidence","confidence":agent.confidence})
        confidence=round(sum(x["confidence"] for x in results)/len(results),2) if results else 0; decision={"alert":alert,"results":results,"confidence":confidence,"recommendation":"Human review required before response"}; self.memory.add(organization_id,"supervisor_decision",decision,confidence); return decision
