class EfficiencyAnalyzer:
    def score(self,workload,capacity):
        total=sum(getattr(workload,x,0) for x in ("investigations","alerts","ingestion_events","correlation_events")); return round(min(1.0,total/max(1,capacity.throughput)),3) if capacity.throughput else 0.0
