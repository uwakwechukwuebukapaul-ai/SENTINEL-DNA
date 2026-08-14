from .repository import ThreatFusionRepository
from .fusion_engine import ThreatFusionEngine
from .actor import ActorEngine
from .campaign import CampaignEngine
class ThreatFusionService:
 def __init__(self): self.repository=ThreatFusionRepository(); self.engine=ThreatFusionEngine(); self.actor=ActorEngine(); self.campaign=CampaignEngine()
 def register_actor(self,**kwargs): return self.repository.save_actor(self.actor.create(**kwargs))
 def register_campaign(self,**kwargs): return self.repository.save_campaign(__import__('services.intelligence.threat_fusion.models',fromlist=['ThreatCampaign']).ThreatCampaign(**kwargs))
 def fuse(self,indicators,**kwargs): return self.engine.fuse(indicators,**kwargs)
 def graph_expansion(self,campaign): return [{"source":campaign.actor,"target":campaign.campaign_id,"relationship":"actor_campaign"}]+[{"source":campaign.campaign_id,"target":i,"relationship":"campaign_ioc"} for i in campaign.indicators]+[{"source":campaign.campaign_id,"target":t,"relationship":"campaign_technique"} for t in campaign.techniques]
