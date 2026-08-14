class ThreatFusionRepository:
 def __init__(self): self.actors={}; self.campaigns={}
 def save_actor(self,a): self.actors[a.actor_id]=a; return a
 def save_campaign(self,c): self.campaigns[c.campaign_id]=c; return c
 def list_actors(self): return list(self.actors.values())
 def list_campaigns(self): return list(self.campaigns.values())
