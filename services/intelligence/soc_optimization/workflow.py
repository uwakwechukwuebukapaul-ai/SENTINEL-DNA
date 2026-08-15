from .models import OptimizationSignal
class WorkflowAnalyzer:
    def analyze(self,tenant_id,signals): return [OptimizationSignal(tenant_id,"WORKFLOW",x.get("category","INSUFFICIENT_DATA"),x.get("workflow_reference",x.get("playbook_reference","")),int(x.get("frequency",0)),x.get("impact","unknown"),x.get("confidence"),x.get("evidence_quality","UNKNOWN"),x.get("status","UNKNOWN"),x.get("references",[]),x.get("provenance",{}),x.get("uncertainty","")) for x in signals or []]
