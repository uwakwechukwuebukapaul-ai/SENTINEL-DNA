class DetectionRecommendationEngine:
 def recommend(self,candidates,coverage=None): return [{"recommendation":c.name,"reason":c.description,"confidence":c.confidence} for c in candidates]+([{"recommendation":"Improve ATT&CK coverage","reason":"Techniques remain without detection visibility","confidence":.8}] if coverage and coverage.get("visibility_gaps") else [])
