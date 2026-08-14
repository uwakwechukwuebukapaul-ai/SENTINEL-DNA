from .models import HuntingHypothesis
class HypothesisEngine:
 def __init__(self,repository): self.repository=repository
 def generate(self,org,source="AI",techniques=None,title="Search for suspicious credential activity"):
  x=HuntingHypothesis(org,title,"Investigate activity deviating from known security behavior",source,techniques or ["T1003"],.91,"HIGH"); self.repository.hypotheses.append(x); return x
