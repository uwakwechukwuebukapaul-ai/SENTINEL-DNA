from .models import AssetRelationship
class AssetGraph:
 def __init__(self,repository): self.repository=repository
 def connect(self,org,source,target,kind,confidence=.8):
  x=AssetRelationship(org,source,target,kind,confidence); self.repository.relationships.append(x); return x
