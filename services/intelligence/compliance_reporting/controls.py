from .models import ControlReport, Provenance
class ControlReportBuilder:
    def build(self,tenant_id,framework_id,controls,drifts=None,readiness=None,history=None):
        drifts={x.control_id:x for x in (drifts or [])}; history=history or []; out=[]
        for c in controls:
            cid=getattr(c,"control_id",""); drift=drifts.get(cid); previous=getattr(drift,"previous_status","") if drift else ""; current=getattr(c,"status","unknown")
            out.append(ControlReport(tenant_id,framework_id,cid,current,previous,current,"changed" if previous and previous!=current else "stable",getattr(readiness,"completeness_score",0.0),getattr(readiness,"freshness_score",0.0),getattr(readiness,"availability_score",0.0),None,drift.to_dict() if drift else None,any(g.get("control_id")==cid for g in getattr(readiness,"gaps",[]) if isinstance(g,dict)),"stable" if len(history)>1 else "insufficient_history",provenance=[Provenance("compliance_monitoring",getattr(drift,"drift_id","") if drift else "","drift and readiness supplied by monitoring")]))
        return out
