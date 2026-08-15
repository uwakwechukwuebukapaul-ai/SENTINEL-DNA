class ComplianceReportingRepository:
    """Tenant-keyed abstraction; replace storage without changing service APIs."""
    def __init__(self): self.reports={}; self.executive={}; self.controls={}; self.trends={}; self.recommendations={}; self.metadata={}
    def _save(self,store,x,key): store[(x.tenant_id,key)]=x; return x
    def save_report(self,x): return self._save(self.reports,x,x.report_id)
    def save_executive(self,x): return self._save(self.executive,x,str(len(self.executive)))
    def save_control(self,x): return self._save(self.controls,x,(x.framework_id,x.control_id))
    def save_trend(self,x): return self._save(self.trends,x,x.framework_id)
    def save_recommendation(self,x,tenant_id): self.recommendations[(tenant_id,x.recommendation_id)]=x; return x
    def list_reports(self,tenant_id): return [x for (t,_),x in self.reports.items() if t==tenant_id]
    def list_executive(self,tenant_id): return [x for (t,_),x in self.executive.items() if t==tenant_id]
    def list_controls(self,tenant_id,framework_id=None): return [x for (t,_),x in self.controls.items() if t==tenant_id and (framework_id is None or x.framework_id==framework_id)]
    def list_trends(self,tenant_id,framework_id=None): return [x for (t,_),x in self.trends.items() if t==tenant_id and (framework_id is None or x.framework_id==framework_id)]
    def list_recommendations(self,tenant_id): return [x for (t,_),x in self.recommendations.items() if t==tenant_id]
