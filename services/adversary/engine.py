from datetime import datetime, timedelta, timezone
from .graph import MitreAttackGraph
from .models import AttackCampaign, AttackStage, ThreatActor
class AdversaryEngine:
    def __init__(self): self.campaigns = {}; self.graph = MitreAttackGraph()
    def create(self, data):
        actor_data = data.get("actor") or {}; actor = ThreatActor(actor_data.get("name", "Synthetic Actor"), actor_data.get("motivation", "unknown"), actor_data.get("target", data.get("target", "enterprise")), actor_data.get("techniques", []), actor_data.get("campaign_history", []))
        stages = [AttackStage(str(x.get("name", x.get("tactic", "stage"))), str(x.get("technique_id", "T1059")), str(x.get("tactic", "Execution")), str(x.get("description", "Synthetic adversary activity")), i) for i, x in enumerate(data.get("stages", []), 1)]
        if not stages: raise ValueError("campaign_requires_stages")
        campaign = AttackCampaign(str(data.get("name", "Synthetic Campaign")), actor, str(data.get("target", actor.target)), stages); self.campaigns[campaign.id] = campaign; return campaign
    def timeline(self, campaign):
        start = datetime.now(timezone.utc); return [{"timestamp": (start + timedelta(minutes=stage.order)).isoformat(), "stage": stage.public()} for stage in campaign.stages]
    def run(self, campaign, hostname="simulated-host"):
        campaign.status = "running"; events = []
        for stage in campaign.stages:
            events.append({"source": "adversary_simulation", "hostname": hostname, "user": campaign.actor.name, "event_type": stage.tactic.lower().replace(" ", "_"), "severity": "high", "technique_id": stage.technique_id, "message": stage.description, "campaign_id": campaign.id})
        campaign.status = "completed"; return {"campaign": campaign.public(), "timeline": self.timeline(campaign), "graph": self.graph.build(campaign.stages), "events": events}
