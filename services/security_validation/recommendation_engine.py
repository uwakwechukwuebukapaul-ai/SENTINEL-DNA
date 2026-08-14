class RecommendationEngine:
 def generate(self,result, gaps=None):
  gaps=gaps or (["detection coverage"] if result<90 else [])
  return [{"gap":gap,"recommendation":"Deploy or tune Sigma coverage and validate the associated control"} for gap in gaps]
