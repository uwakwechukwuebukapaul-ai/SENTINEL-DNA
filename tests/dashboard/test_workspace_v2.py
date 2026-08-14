from services.intelligence.copilot import InvestigationCopilot


def test_copilot_uses_canonical_intelligence_fields():
    intelligence = {"risk_score": 88, "risk_severity": "high", "confidence": 0.9,
                    "findings": ["Suspicious login"], "attack_story": "Credential access",
                    "recommendations": ["Reset credentials"]}
    copilot = InvestigationCopilot()
    assert "88" in copilot.explain(intelligence)
    assert copilot.summarize_attack_story(intelligence) == "Credential access"
    assert copilot.suggest_actions(intelligence) == ["Reset credentials"]
    assert len(copilot.questions(intelligence)) == 3
