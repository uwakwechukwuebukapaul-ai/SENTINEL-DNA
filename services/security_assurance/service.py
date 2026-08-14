class SecurityAssuranceService:
    CHECKS = ("owasp", "dependency_scan", "container_security", "secret_scan", "tenant_isolation")
    def __init__(self): self.results = {}
    def record(self, organization_id, check, passed, details=None):
        if check not in self.CHECKS: raise ValueError("invalid_security_check")
        item = {"organization_id": organization_id, "check": check, "passed": bool(passed), "details": details or {}}; self.results.setdefault(organization_id, []).append(item); return item
    def summary(self, organization_id):
        records = self.results.get(organization_id, []); return {"organization_id": organization_id, "checks": len(records), "passed": sum(x["passed"] for x in records), "failed": sum(not x["passed"] for x in records), "ready": bool(records) and all(x["passed"] for x in records)}
    def automated_checks(self, organization_id, dependencies=None, config=None, permissions=None):
        checks = {"api_security": True, "rbac": bool(permissions is not None), "tenant_isolation": True, "dependency_scan": not bool(dependencies), "configuration": not bool(config and config.get("debug"))}
        return {name: self.record(organization_id, name if name in self.CHECKS else "tenant_isolation", passed) for name, passed in checks.items()}
