from .models import RecurringPattern
class PatternAnalyzer:
    def analyze(self,tenant_id,outcomes):
        groups={}
        for x in outcomes: key=("false_positive",x.detection_reference) if x.false_positive_signal in {"confirmed","probable"} else ("resolution",x.resolution_status); groups.setdefault(key,[]).append(x)
        return [RecurringPattern(tenant_id,k[0],k[1],len(v),[x.outcome_id for x in v],None,{"source_subsystem":"outcome_learning"}) for k,v in sorted(groups.items()) if len(v)>=2]
