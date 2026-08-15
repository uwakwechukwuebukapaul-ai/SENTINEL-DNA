class AutomationIntelligenceRepository:
    def __init__(self): self.experiences={}; self.recommendations={}
    def save_experience(self,x): self.experiences[(x.tenant_id,x.experience_id)]=x; return x
    def get_experience(self,i,t): return self.experiences.get((t,i))
    def list_experiences(self,t,workflow_id=None): return [x for (tenant,_),x in self.experiences.items() if tenant==t and (workflow_id is None or x.workflow_id==workflow_id)]
    def save_recommendation(self,x): self.recommendations[(x.tenant_id,x.recommendation_id)]=x; return x
    def list_recommendations(self,t): return [x for (tenant,_),x in self.recommendations.items() if tenant==t]
