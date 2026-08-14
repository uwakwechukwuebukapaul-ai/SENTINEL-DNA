class IntelligenceConfidenceEngine:
 def calculate(self,source_reliability=.5,relationship_strength=.5,historical_matches=0): return round(min(1,source_reliability*.4+relationship_strength*.4+min(1,historical_matches/5)*.2),4)
