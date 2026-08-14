from copy import deepcopy
from services.intelligence.copilot.copilot_engine import InvestigationCopilot


def data():
    return {"case_id": "C-1", "evidence": [{"evidence_id": "E-1", "description": "phishing email"}], "iocs": [{"id": "I-1"}], "timeline": [{"id": "T-1"}]}, {"case_id": "C-1", "confidence": .88, "mitre": ["T1566"], "recommendations": ["Review headers"]}, {"summary": "Potential credential harvesting", "confidence": .88, "findings": [{"finding_id": "RF-1"}]}, {"verdict": "true_positive", "recommended_actions": ["Escalate"]}


def test_copilot_summary_generation(): assert InvestigationCopilot().summarize_investigation(*data(), "MEM-1").answer
def test_copilot_question_answering(): assert "T1566" in InvestigationCopilot().answer_question("What MITRE techniques are involved?", *data(), "MEM-1").answer
def test_copilot_evidence_references(): assert InvestigationCopilot().summarize_investigation(*data(), "MEM-1").evidence_refs == ["E-1"]
def test_copilot_recommendations(): assert InvestigationCopilot().recommend_next_steps(*data(), "MEM-1").recommended_actions
def test_copilot_does_not_modify_context():
    args = data(); before = deepcopy(args[0]); InvestigationCopilot().summarize_investigation(*args, "MEM-1"); assert args[0] == before
def test_copilot_runtime_integration(): assert InvestigationCopilot().summarize_investigation(*data(), "MEM-1").metadata["synthetic_only"]
