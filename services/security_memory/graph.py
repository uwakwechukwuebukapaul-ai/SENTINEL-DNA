from .models import KnowledgeEntity,KnowledgeRelationship
class KnowledgeGraphEngine:
 def __init__(self): self.entities=[]; self.relationships=[]
 def add_entity(self,org,data): x=KnowledgeEntity(org,data.get("entity_type","INCIDENT"),data.get("name",""),data.get("description",""),float(data.get("confidence",.8)),data.get("metadata",{})); self.entities.append(x); return x
 def relate(self,org,data): x=KnowledgeRelationship(org,data.get("source_entity",""),data.get("target_entity",""),data.get("relationship_type","RELATED_TO"),float(data.get("confidence",.8)),data.get("evidence",[])); self.relationships.append(x); return x
 def search(self,org,term): return [x for x in self.entities if term.lower() in (x.name+" "+x.description).lower() and x.organization_id==org]
