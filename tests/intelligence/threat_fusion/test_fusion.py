from services.intelligence.threat_fusion import ThreatActor,ThreatCampaign,ThreatFusionService
def test_actor_models(): assert ThreatActor("a","Actor").to_dict()["name"]=="Actor"
def test_campaign_correlation(): c=ThreatCampaign("c","Campaign","a",["evil.com"]); assert ThreatFusionService().campaign.correlate(c,["evil.com"])
def test_ioc_fusion(): assert ThreatFusionService().fuse(["evil.com"],cases=["C-1"])["matched_iocs"]==["evil.com"]
def test_confidence_scoring(): assert ThreatFusionService().fuse([],cases=["C"])["confidence"]>.4
def test_graph_expansion():
 s=ThreatFusionService(); c=s.register_campaign(campaign_id="c",name="C",actor="a",indicators=["i"],techniques=["T1566"]); assert len(s.graph_expansion(c))==3
def test_backward_compatibility(): assert "threat_fusion_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
