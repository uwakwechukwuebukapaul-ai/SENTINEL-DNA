class DetectionIntelligenceRepository:
 def __init__(self): self.candidates={}
 def save(self,c): self.candidates[c.candidate_id]=c; return c
 def list(self): return list(self.candidates.values())
