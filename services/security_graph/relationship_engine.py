class RelationshipEngine:
 def relate(self,repository,source,target,relationship_type,confidence=.8,evidence=""): return repository.add_relationship(__import__('services.security_graph.graph_builder',fromlist=['GraphBuilder']).GraphBuilder().relationship(source.tenant_id,source,target,relationship_type,confidence,evidence))
