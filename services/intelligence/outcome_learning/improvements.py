from .models import ImprovementCandidate
class ImprovementGenerator:
    def generate(self,tenant_id,outcomes,patterns):
        result=[]
        for p in patterns:
            category="DETECTION" if p.pattern_type=="false_positive" else "WORKFLOW"; result.append(ImprovementCandidate(tenant_id,category,"Review recurring "+p.pattern_type+" pattern",f"{p.count} tenant-scoped outcomes share pattern {p.key}; authorized human review is recommended.",p.outcome_references,[],None,"high" if p.count>=3 else "medium",provenance=p.provenance))
        return result
