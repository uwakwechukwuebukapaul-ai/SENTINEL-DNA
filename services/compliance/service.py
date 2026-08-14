class ComplianceService:
    FRAMEWORKS = {"NIST_CSF": ("Identify", "Protect", "Detect", "Respond", "Recover"), "ISO_27001": ("A.5", "A.8", "A.12", "A.17"), "SOC_2": ("security", "availability", "confidentiality", "privacy")}
    def __init__(self): self.controls = {}
    def track(self, organization_id, framework, control, status=" not_started", evidence=None):
        if framework not in self.FRAMEWORKS: raise ValueError("unsupported_framework")
        item = {"organization_id": organization_id, "framework": framework, "control": control, "status": status.strip(), "evidence": evidence or []}; self.controls.setdefault(organization_id, []).append(item); return item
    def summary(self, organization_id):
        records = self.controls.get(organization_id, []); return {"organization_id": organization_id, "controls": len(records), "complete": sum(x["status"] in {"complete", "implemented"} for x in records), "frameworks": sorted({x["framework"] for x in records})}
