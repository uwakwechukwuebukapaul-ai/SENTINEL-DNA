class DrillDownService:
    """Tenant-scoped presentation lookup; authoritative records remain external."""
    def __init__(self, source_resolver=None): self.source_resolver=source_resolver
    def _get(self, tenant_id, kind, reference):
        if not self.source_resolver: return None
        value=self.source_resolver(tenant_id, kind, str(reference))
        if not value or value.get("tenant_id", tenant_id) != tenant_id: return None
        return dict(value)
    def attention(self, tenant_id, reference): return self._get(tenant_id,"attention",reference)
    def investigation(self, tenant_id, reference): return self._get(tenant_id,"investigation",reference)
    def evidence(self, tenant_id, reference):
        value=self._get(tenant_id,"evidence",reference)
        return value or {"evidence_id":str(reference),"status":"unavailable","requires_human_review":True,"uncertainty":"UNKNOWN","tenant_id":tenant_id}
    def risk(self, tenant_id, reference): return self._get(tenant_id,"risk",reference)
    def compliance(self, tenant_id, reference): return self._get(tenant_id,"compliance",reference)
    def decision(self, tenant_id, reference): return self._get(tenant_id,"decision",reference)
    def lifecycle(self, tenant_id, reference): return self._get(tenant_id,"lifecycle",reference)
    def history(self, tenant_id, reference): return self._get(tenant_id,"history",reference) or {"reference":str(reference),"status":"unknown","uncertainty":"UNKNOWN","tenant_id":tenant_id}
    def copilot_context(self, tenant_id, context):
        context=dict(context or {}); context["tenant_id"]=tenant_id; context.setdefault("uncertainty","UNKNOWN"); context.setdefault("requires_human_review",True); context["tts_enabled"]=False; return context
