def score_threat(reputation=0, historical_frequency=0, campaign_similarity=0, evidence_confidence=0, mitre_relevance=0):
    score = round(min(100, max(0, reputation * .30 + historical_frequency * .20 + campaign_similarity * .20 + evidence_confidence * .20 + mitre_relevance * .10)))
    severity = "low" if score <= 30 else "medium" if score <= 70 else "high"
    return {"score": score, "severity": severity}
