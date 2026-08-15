class OutcomeLearningRepository:
    def __init__(self): self.outcomes={}; self.quality={}; self.patterns={}; self.improvements={}
    def save_outcome(self,x): self.outcomes[(x.tenant_id,x.outcome_id)]=x; return x
    def list_outcomes(self,t): return [x for (tenant,_),x in self.outcomes.items() if tenant==t]
    def save_quality(self,x): self.quality[(x.tenant_id,x.outcome_id)]=x; return x
    def list_quality(self,t): return [x for (tenant,_),x in self.quality.items() if tenant==t]
    def save_patterns(self,items):
        for x in items:self.patterns[(x.tenant_id,x.pattern_type,x.key)]=x
    def list_patterns(self,t): return [x for (tenant,_,_),x in self.patterns.items() if tenant==t]
    def save_improvements(self,items):
        for x in items:self.improvements[(x.tenant_id,x.candidate_id)]=x
    def list_improvements(self,t): return [x for (tenant,_),x in self.improvements.items() if tenant==t]
