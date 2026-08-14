from services.intelligence.threat_intelligence import ThreatCorrelationEngine, ThreatIndicator, ThreatIntelligenceRepository
from services.intelligence.threat_intelligence.scoring import score_threat

def test_indicator_storage():
    r=ThreatIntelligenceRepository(); i=ThreatIndicator("I-1","domain","evil.test"); r.add_indicator(i); assert r.get_indicator("I-1").value == "evil.test"
def test_indicator_lookup():
    r=ThreatIntelligenceRepository(); r.add_indicator(ThreatIndicator("I-1","domain","evil.test")); assert r.search_indicator("evil.test")[0].indicator_id == "I-1"
def test_case_correlation():
    r=ThreatIntelligenceRepository(); e=ThreatCorrelationEngine(r); e.correlate_case({"case_id":"C-1"}, iocs=[{"id":"I","type":"domain","value":"evil.test"}]); assert r.get_related_cases("TI-" + __import__('hashlib').sha256(b"domain|evil.test").hexdigest()[:16]) == ["C-1"]
def test_campaign_similarity():
    r=ThreatIntelligenceRepository(); e=ThreatCorrelationEngine(r); e.correlate_case({"case_id":"C-1"},iocs=[{"value":"evil.test","type":"domain"}]); x=e.correlate_case({"case_id":"C-2"},iocs=[{"value":"evil.test","type":"domain"}]); assert x.campaign_similarity > 0
def test_threat_scoring(): assert score_threat(100,100,100,100,100)["score"] == 100
def test_result_serialization(): assert ThreatCorrelationEngine().correlate_case({"case_id":"C"}).to_dict()["case_id"] == "C"
def test_non_blocking_failure(): assert ThreatCorrelationEngine().correlate_case({"case_id":"C"}).synthetic_only
