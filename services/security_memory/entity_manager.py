class EntityManager:
 def __init__(self,graph): self.graph=graph
 def create(self,org,data): return self.graph.add_entity(org,data)
