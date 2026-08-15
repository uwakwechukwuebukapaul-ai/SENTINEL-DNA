from .models import GovernanceSignal, DecisionProvenance
class GovernanceSignalBuilder:
    def build(self,tenant_id,inputs):
        result=[]
        for item in inputs or []:
            if isinstance(item,GovernanceSignal): result.append(item); continue
            source=str(item.get("source_subsystem",item.get("category","unknown"))); result.append(GovernanceSignal(tenant_id, item.get("category","governance_dependency"), item.get("value"), item.get("severity","medium"), item.get("direction","stable"), float(item.get("confidence",0.0)), list(item.get("evidence_references",[])), list(item.get("source_references",[])), list(item.get("affected_controls",[])), list(item.get("affected_assets",[])), [DecisionProvenance(source,item.get("source_reference",""),item.get("basis","observed source intelligence"))]))
        return result
