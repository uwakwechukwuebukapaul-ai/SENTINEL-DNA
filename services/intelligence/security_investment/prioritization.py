from .models import InvestmentPriority
class InvestmentPrioritizer:
    def score(self,opportunity,risk=0.0,business_impact=0.0):
        value=max(0.0,1-opportunity.current_control_effectiveness); return round(min(100,risk*.45+business_impact*.4+value*100*.15),2)
    def prioritize(self,tenant_id,items):
        ranked=sorted(items,key=lambda x:x["score"],reverse=True); return [InvestmentPriority(str(i+1),tenant_id,x["opportunity"].opportunity_id,x["score"],i+1,"Prioritized by risk, business impact, and control gap.") for i,x in enumerate(ranked)]
