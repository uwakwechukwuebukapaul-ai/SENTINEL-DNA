class SecurityAssessment:
    def run(self, dependencies=None, config=None, secrets=None, permissions=None):
        return {"dependency_scanning": not bool(dependencies and any(x.get("vulnerable") for x in dependencies)), "configuration_validation": not bool(config and config.get("debug")), "secret_detection": not bool(secrets), "permission_auditing": not bool(permissions and any(not x.get("allowed") for x in permissions))}
