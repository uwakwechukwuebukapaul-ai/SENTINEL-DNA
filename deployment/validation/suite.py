class DeploymentValidationSuite:
    TESTS = ("fresh_installation", "upgrade", "rollback", "backup_restore")
    def run(self, checks=None):
        checks = checks or {}; return {name: {"passed": bool(checks.get(name, False)), "required": True} for name in self.TESTS}
    def ready(self, checks=None): return all(item["passed"] for item in self.run(checks).values())
