class WorkloadAnalyzer:
    FIELDS=("investigations","alerts","ingestion_events","correlation_events","hunting_queries","automation_requests","copilot_requests","connector_operations")
    def total(self,snapshot): return sum(getattr(snapshot,x,0) for x in self.FIELDS)
    def pressure(self,snapshot): return {x:getattr(snapshot,x,0) for x in self.FIELDS if getattr(snapshot,x,0)}
