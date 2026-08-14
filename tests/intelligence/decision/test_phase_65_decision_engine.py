from services.intelligence.decision.engine import DecisionEngine


def make(text, confidence=.9, severity="high"):
    return DecisionEngine().decide({"case_id": "C-1", "risk": {"severity": severity}, "confidence": confidence, "findings": [text], "artifacts": [{"id": "E-1"}], "mitre": ["T1566"]}, {"summary": text, "confidence": confidence}, "MEM-1")


def test_malicious_phishing_produces_true_positive(): assert make("malicious phishing credential harvesting").verdict == "true_positive"
def test_weak_evidence_produces_needs_review(): assert make("suspicious indicator", severity="low").verdict == "needs_review"
def test_benign_investigation_produces_false_positive(): assert make("benign legitimate activity", severity="low").verdict == "false_positive"
def test_serialization_works(): assert make("benign").to_dict()["decision_id"].startswith("DEC-")
def test_duplicate_execution_safe(): assert make("malicious phishing").to_dict() == make("malicious phishing").to_dict()
