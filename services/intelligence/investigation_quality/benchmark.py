from .models import QualityBenchmark
class QualityBenchmarkEngine:
    def benchmark(self, tenant_id, assessments):
        items=list(assessments); average=round(sum(x.overall_score for x in items)/len(items),2) if items else 0.0; trend="stable"
        if len(items)>1: trend="improving" if items[-1].overall_score>items[0].overall_score else "declining" if items[-1].overall_score<items[0].overall_score else "stable"
        return QualityBenchmark(tenant_id, average, len(items), trend)
