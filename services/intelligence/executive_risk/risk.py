class ExecutiveRiskEngine:
    def score(self,asset,security_risk=0.0,exposure=0.0,threat_confidence=0.0):
        business=(asset.business_value+asset.regulatory_impact+asset.revenue_impact+asset.operational_impact)/4; score=round(min(100,(business*.45+security_risk*.3+exposure*.2+threat_confidence*.05)),2); return score
    def level(self,score): return "critical" if score>=80 else "high" if score>=60 else "medium" if score>=30 else "low"
