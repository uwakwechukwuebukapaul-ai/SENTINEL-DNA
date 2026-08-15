class ObservabilityAnalytics:
    def anomalies(self,metrics,error_threshold=.5): return [x for x in metrics if x.metric_type=="error_rate" and x.value>=error_threshold]
    def trends(self,metrics):
        return {service:{"latest":max((x.timestamp for x in metrics if x.service_name==service),default=None),"count":sum(1 for x in metrics if x.service_name==service)} for service in {x.service_name for x in metrics}}
