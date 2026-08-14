from .models import AgentMemory
class AgentMemoryStore:
    def __init__(self): self.entries=[]
    def add(self, org, kind, content, confidence=0): item=AgentMemory(org,kind,content,confidence); self.entries.append(item); return item
    def scoped(self, org): return [x for x in self.entries if x.organization_id==org]
