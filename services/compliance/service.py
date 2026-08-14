class ComplianceService:
    FRAMEWORKS = {"NIST_CSF": ("Identify", "Protect", "Detect", "Respond", "Recover"), "ISO_27001": ("A.5", "A.8", "A.12", "A.17"), "SOC_2": ("security", "availability", "confidentiality", "privacy")}
    def __init__(self):
        self.controls = {}
        from .repository import ComplianceRepository
        from .evaluator import ComplianceEvaluator
        from .frameworks import DEFAULT_CONTROLS
        from .risk_engine import RiskEngine
        self.repository=ComplianceRepository(); self.evaluator=ComplianceEvaluator(); self.risk_engine=RiskEngine(); self.default_controls=DEFAULT_CONTROLS
    def assess_framework(self,tenant_id,framework_id="NIST_CSF",capabilities=None): return [self.repository.create_assessment(a) for a in self.evaluator.evaluate_framework(tenant_id,self.default_controls,capabilities)]
    def get_control_status(self,tenant_id): return [a.to_dict() for a in self.repository.list_assessments(tenant_id)]
    def get_security_posture(self,tenant_id,**kwargs): return self.risk_engine.calculate(tenant_id,compliance_gaps=max(1, len(self.evaluator.generate_gap_report(self.repository.list_assessments(tenant_id)))),**kwargs)
    def generate_risk_report(self,tenant_id,**kwargs): return self.get_security_posture(tenant_id,**kwargs)
    def track(self, organization_id, framework, control, status=" not_started", evidence=None):
        if framework not in self.FRAMEWORKS: raise ValueError("unsupported_framework")
        item = {"organization_id": organization_id, "framework": framework, "control": control, "status": status.strip(), "evidence": evidence or []}; self.controls.setdefault(organization_id, []).append(item); return item
    def summary(self, organization_id):
        records = self.controls.get(organization_id, []); return {"organization_id": organization_id, "controls": len(records), "complete": sum(x["status"] in {"complete", "implemented"} for x in records), "frameworks": sorted({x["framework"] for x in records})}
