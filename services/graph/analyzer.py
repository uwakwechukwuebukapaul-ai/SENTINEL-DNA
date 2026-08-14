class ThreatGraphAnalyzer:
    def __init__(self, repository): self.repository=repository
    def entity(self, org, entity_id): return [x.public() for x in self.repository.scoped(self.repository.nodes,org) if x.entity_id==entity_id]
    def path(self, org, incident_id): return {"incident_id":incident_id,"nodes":[x.public() for x in self.repository.scoped(self.repository.nodes,org)],"relationships":[x.public() for x in self.repository.scoped(self.repository.relationships,org)],"risk":0,"confidence":.7,"mitre_mapping":[]}
    def blast_radius(self, org, entity_id): return {"entity_id":entity_id,"affected_assets":[x.target_id for x in self.repository.scoped(self.repository.relationships,org) if x.source_id==entity_id]}
