from services.intelligence.hunting import HuntQueryEngine, HuntManager

def context(): return {"case_id":"C-1","iocs":[{"type":"domain","value":"malicious-login.com"}],"mitre":["T1566"],"behavior":"credential theft"}
def test_ioc_search(): assert HuntQueryEngine().search_ioc("malicious-login.com", context()).related_indicators == ["malicious-login.com"]
def test_case_search(): assert HuntQueryEngine().search_cases("C-1", context()).related_cases == ["C-1"]
def test_mitre_search(): assert HuntQueryEngine().search_mitre("T1566", context()).matches
def test_campaign_search(): assert HuntQueryEngine().search_campaigns("malicious-login.com", context()).synthetic_only
def test_behavior_search(): assert HuntQueryEngine().search_behavior("credential theft", context()).matches
def test_hunt_manager():
    manager=HuntManager(); hunt=manager.create_hunt("Credential hunt","Find credential theft",["T1566"]); result=manager.run_hunt(hunt.hunt_id,"credential theft",context()); assert result.matches and hunt.status == "completed"
def test_serialization(): assert "query_id" in HuntQueryEngine().search_ioc("none",context()).to_dict()
