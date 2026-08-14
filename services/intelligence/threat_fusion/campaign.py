from .models import ThreatCampaign
class CampaignEngine:
 def correlate(self,campaign,indicators): return [x for x in campaign.indicators if x in indicators]
