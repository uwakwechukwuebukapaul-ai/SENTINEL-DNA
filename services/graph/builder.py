from .models import SecurityNode, SecurityRelationship
class ThreatGraphBuilder:
    def __init__(self, repository): self.repository=repository
    def build_from_events(self, org, events):
        for e in events:
            if e.user_id and e.asset_id:
                self.repository.nodes.extend([SecurityNode(org,e.user_id,"USER"),SecurityNode(org,e.asset_id,"ASSET")]); self.repository.relationships.append(SecurityRelationship(org,e.user_id,"logged_into",e.asset_id))
        return self.repository
