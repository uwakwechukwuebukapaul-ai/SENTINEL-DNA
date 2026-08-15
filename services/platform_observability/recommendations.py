class ObservabilityRecommendations:
    def generate(self,health):
        return [{"service_name":x.service_name,"severity":"high" if x.status=="unhealthy" else "medium","recommendation":"Investigate elevated platform error rate","requires_human_review":True} for x in health if x.status!="healthy"]
