from datetime import datetime, timezone
class IntegrationHealthService:
    def __init__(self,registry): self.registry=registry; self.health={}
    def check_connector(self,connector_id): x=self.registry.get_connector(connector_id); h=x.health_check(); self.health[connector_id]={"connector_id":connector_id,"status":h.get("status","healthy"),"last_check":datetime.now(timezone.utc).isoformat(),"latency":0.0,"error_count":0,"message":"synthetic"}; return self.health[connector_id]
    def get_health(self,connector_id): return self.health.get(connector_id)
    def get_system_health(self): return {"healthy_connectors":sum(x["status"]=="healthy" for x in self.health.values()),"failed_connectors":sum(x["status"]!="healthy" for x in self.health.values()),"last_checked":max((x["last_check"] for x in self.health.values()),default=None)}
