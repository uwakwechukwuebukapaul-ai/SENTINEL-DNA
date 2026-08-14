class ThreatRepository:
    def __init__(self): self.indicators = {}; self.actors = {}; self.campaigns = {}
    def indicators_for(self, organization_id): return [x for x in self.indicators.values() if x.organization_id == organization_id]
    def actors_for(self, organization_id): return [x for x in self.actors.values() if x.organization_id == organization_id]
    def campaigns_for(self, organization_id): return [x for x in self.campaigns.values() if x.organization_id == organization_id]
