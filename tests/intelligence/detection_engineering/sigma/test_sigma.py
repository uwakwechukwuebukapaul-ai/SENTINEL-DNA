from services.intelligence.detection_engineering.sigma import SigmaParser,SigmaRuleRepository
from services.intelligence.mitre_coverage import MITRECoverageEngine
def rule(): return {"title":"Suspicious Login Activity","logsource":{"product":"windows"},"detection":{"selection":{"failed_login":True}},"level":"high","tags":["attack.t1110"]}
def test_sigma_parse(): assert SigmaParser().parse_rule(rule()).title.startswith("Suspicious")
def test_sigma_validation(): assert SigmaParser().validate_rule(rule()) and not SigmaParser().validate_rule({})
def test_sigma_serialization(): assert "detection_logic" in SigmaParser().parse_rule(rule()).to_dict()
def test_rule_repository():
 r=SigmaRuleRepository(); x=SigmaParser().parse_rule(rule()); r.save_rule(x); assert r.search_rules("login")[0].rule_id == x.rule_id
def test_mitre_coverage():
 x=SigmaParser().parse_rule(rule()); assert MITRECoverageEngine().calculate_coverage([x],["T1110","T1059"])["covered"] == ["T1110"]
def test_detection_gap_analysis(): assert "T1059" in MITRECoverageEngine().get_missing_techniques([SigmaParser().parse_rule(rule())],["T1059"]).missing_techniques
def test_detection_recommendation(): assert MITRECoverageEngine().get_missing_techniques([], ["T1059"]).recommendation
def test_deterministic_output(): assert SigmaParser().parse_rule(rule()).to_dict() == SigmaParser().parse_rule(rule()).to_dict()
