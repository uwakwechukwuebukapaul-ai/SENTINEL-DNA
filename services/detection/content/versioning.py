from .models import DetectionRuleVersion
class RuleVersioning:
    def __init__(self, repository): self.repository = repository
    def create(self, rule, changes, author_id):
        versions = self.repository.versions.setdefault(rule.id, []); item = DetectionRuleVersion(rule.id, len(versions) + 1, changes, author_id); versions.append(item); rule.version = item.version_number; return item
    def compare(self, rule_id, first, second):
        versions = self.repository.versions.get(rule_id, []); return {"first": next((x.public() for x in versions if x.version_number == first), None), "second": next((x.public() for x in versions if x.version_number == second), None)}
    def rollback(self, rule, version_number): rule.version = version_number; return rule
