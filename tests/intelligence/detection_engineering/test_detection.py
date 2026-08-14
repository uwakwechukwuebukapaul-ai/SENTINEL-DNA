from services.intelligence.detection_engineering import DetectionEngineeringService
def test_rule_creation(): assert DetectionEngineeringService().get_detection_catalog()
def test_rule_serialization(): assert "id" in DetectionEngineeringService().get_detection_catalog()[0]
def test_phishing_detection(): assert "PHISHING_LINK_DETECTION" in DetectionEngineeringService().evaluate_security_event({"description":"phishing malicious url credential"}).matched_rules
def test_bruteforce_detection(): assert "BRUTE_FORCE_AUTH_DETECTION" in DetectionEngineeringService().evaluate_security_event({"description":"repeated failed login"}).matched_rules
def test_malware_detection(): assert "MALWARE_INDICATOR_DETECTION" in DetectionEngineeringService().evaluate_security_event({"description":"ransomware suspicious execution"}).matched_rules
def test_network_detection(): assert "NETWORK_ANOMALY_DETECTION" in DetectionEngineeringService().evaluate_security_event({"description":"unusual outbound beaconing"}).matched_rules
def test_detection_metrics(): assert DetectionEngineeringService().get_detection_metrics()["total_rules"] == 4
def test_deterministic_output():
    s=DetectionEngineeringService(); assert s.evaluate_security_event({"event_id":"E","description":"phishing"}).to_dict()["matched_rules"] == s.evaluate_security_event({"event_id":"E","description":"phishing"}).to_dict()["matched_rules"]
