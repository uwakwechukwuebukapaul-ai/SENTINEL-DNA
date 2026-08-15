class TelemetryAggregator:
    def aggregate(self,metrics):
        return {"metric_count":len(metrics),"services":sorted({x.service_name for x in metrics}),"by_type":{kind:sum(1 for x in metrics if x.metric_type==kind) for kind in {x.metric_type for x in metrics}}}
