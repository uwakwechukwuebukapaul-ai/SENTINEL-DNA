from .models import DetectionRule, DetectionPackage
from .repository import DetectionContentRepository
from .validator import DetectionRuleValidator
from .versioning import RuleVersioning
from .testing import DetectionTestEngine
class DetectionContentService:
    def __init__(self, repository=None): self.repository = repository or DetectionContentRepository(); self.validator = DetectionRuleValidator(); self.versioning = RuleVersioning(self.repository); self.tester = DetectionTestEngine()
    def create(self, organization_id, data, author_id=None):
        result = self.validator.validate(data)
        if not result["valid"]: raise ValueError(result)
        return self.repository.save_rule(DetectionRule(organization_id, data["name"], data["description"], str(data["severity"]).upper(), author_id, data["query_logic"], data["data_source"], data.get("mitre_techniques", []), data.get("tags", [])))
    def update(self, rule, changes, author_id): self.versioning.create(rule, changes, author_id); [setattr(rule, key, value) for key, value in changes.items() if hasattr(rule, key)]; return self.repository.save_rule(rule)
    def test(self, rule, events): return self.tester.test(rule, events)
    def deploy(self, rule):
        if rule.status == "DRAFT": rule.status = "TESTING"
        elif rule.status == "TESTING": rule.status = "APPROVED"
        elif rule.status == "APPROVED": rule.status = "ACTIVE"
        else: raise ValueError("invalid_deployment_state")
        return rule
    def packages(self, organization_id): return [x for x in self.repository.packages.values() if x.organization_id == organization_id]
