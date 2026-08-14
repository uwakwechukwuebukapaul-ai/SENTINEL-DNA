class DetectionContentRepository:
    def __init__(self): self.rules = {}; self.versions = {}; self.packages = {}; self.tests = {}; self.analytics = {}
    def save_rule(self, rule): self.rules[rule.id] = rule; return rule
    def get_rule(self, rule_id, organization_id):
        rule = self.rules.get(rule_id); return rule if rule and rule.organization_id == organization_id else None
    def list_rules(self, organization_id): return [x for x in self.rules.values() if x.organization_id == organization_id]
