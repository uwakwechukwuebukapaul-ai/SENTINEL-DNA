class RelationshipManager:
 def __init__(self,graph): self.graph=graph
 def related(self,org,entity_id): return [x for x in self.graph.relationships if x.organization_id==org and (x.source_entity==entity_id or x.target_entity==entity_id)]
