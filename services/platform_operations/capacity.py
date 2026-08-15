class CapacityAnalyzer:
    def evaluate(self,snapshot):
        severity="critical" if snapshot.utilization>=.9 or snapshot.error_rate>=.5 else "high" if snapshot.utilization>=.75 or snapshot.error_rate>=.2 else "low"
        return {"service_name":snapshot.service_name,"severity":severity,"pressure":max(snapshot.utilization,snapshot.error_rate),"available_capacity":snapshot.available_capacity}
