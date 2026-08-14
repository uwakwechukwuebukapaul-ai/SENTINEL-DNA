from services.intelligence.reporting.narrative_engine import InvestigationNarrativeEngine

def args(): return ({"case_id":"C-1","evidence":[{"evidence_id":"E-1"}],"timeline":[{"event":"email"}]},{"case_id":"C-1","confidence":.88,"mitre":["T1566"],"recommendations":["Review"]},{"summary":"Phishing detected","confidence":.88},{"rationale":"Malicious"},{"answer":"Phishing"},"MEM-1")
def test_narrative_generation(): assert InvestigationNarrativeEngine().generate_report(*args()).case_id == "C-1"
def test_executive_summary(): assert "Confidence" in InvestigationNarrativeEngine().generate_executive_summary(*args())
def test_attack_story_generation(): assert "T1566" in InvestigationNarrativeEngine().generate_incident_story(*args())
def test_timeline_rendering(): assert "email" in InvestigationNarrativeEngine().generate_incident_story(*args())
def test_serialization(): assert "report_id" in InvestigationNarrativeEngine().generate_report(*args()).to_dict()
def test_non_blocking_failure(): assert InvestigationNarrativeEngine().generate_report(*args()).synthetic_only
