from services.intelligence.threat.service import ThreatIntelligenceService
from services.intelligence.threat.scoring import ThreatScoringEngine
def test_ioc_enrichment_and_tenant_isolation():
    service=ThreatIntelligenceService(); item=service.create_indicator("org-a",{"indicator_type":"IP","value":"203.0.113.5","source":"feed","confidence":95}); assert service.enrich("org-a",item.value)["reputation"]=="malicious"; assert service.enrich("org-b",item.value)["reputation"]=="unknown"
def test_threat_scoring(): assert ThreatScoringEngine().score(95,0,100,100,2,1)["severity"]=="CRITICAL"
def test_feed_and_actor_boundaries():
    service=ThreatIntelligenceService(); assert service.actors("org-a")==[]; assert service.campaigns("org-a")==[]
