class ProductionChecklist:
    ITEMS = ("cloud_deployment", "environment", "database_migrations", "backup_verification", "restore_verification")
    def validate(self, results=None):
        results = results or {}; return {item: {"passed": bool(results.get(item, False)), "required": True} for item in self.ITEMS}
    def ready(self, results=None): return all(x["passed"] for x in self.validate(results).values())
