from services.intelligence.soar import SOARService
def test_playbook_serialization(): assert "id" in SOARService().repository.get_playbook("PHISHING_RESPONSE_PLAYBOOK").to_dict()
def test_safe_playbook_generation(): assert SOARService().suggest_automation({"findings":"phishing"})["playbook"] == "PHISHING_RESPONSE_PLAYBOOK"
def test_soar_planning(): assert SOARService().suggest_automation({"findings":"malware"})["approval_required"]
def test_approval_required(): assert SOARService().request_execution("PHISHING_RESPONSE_PLAYBOOK","C-1").status == "blocked"
def test_execution_blocking():
 s=SOARService(); s.request_execution("PHISHING_RESPONSE_PLAYBOOK","C-1"); s.approve_execution("EXE-PHISHING_RESPONSE_PLAYBOOK-C-1","analyst"); assert s.execute_playbook("PHISHING_RESPONSE_PLAYBOOK","C-1").status == "completed"
def test_audit_logging(): assert SOARService().request_execution("MALWARE_RESPONSE_PLAYBOOK","C-1") and len(SOARService().audit.events) >= 0
def test_execution_history(): assert len(SOARService().get_execution_history()) == 0
def test_deterministic_behavior(): assert SOARService().suggest_automation({"findings":"phishing"}) == SOARService().suggest_automation({"findings":"phishing"})
