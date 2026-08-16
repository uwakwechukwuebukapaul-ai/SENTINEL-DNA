class DataFabricQualityAnalytics:
    def derive(self,tenant_id,report): return {"tenant_id":tenant_id,"quality":report.to_dict(),"observed_vs_derived":{"observed_event_count":report.observed_event_count,"quality_score":"derived"},"advisory_only":True}
