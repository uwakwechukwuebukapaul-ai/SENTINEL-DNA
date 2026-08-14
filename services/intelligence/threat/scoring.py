class ThreatScoringEngine:
    def score(self, confidence=0, age_days=0, campaign_relevance=0, actor_association=0, detection_matches=0, previous_incidents=0):
        value = min(100, round(float(confidence) * .35 + max(0, 20 - age_days) + campaign_relevance * .2 + actor_association * .15 + detection_matches * 5 + previous_incidents * 5)); severity = "CRITICAL" if value >= 85 else "HIGH" if value >= 65 else "MEDIUM" if value >= 35 else "LOW"; return {"score": value, "severity": severity}
