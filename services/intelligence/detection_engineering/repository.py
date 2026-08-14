from __future__ import annotations
from .models import DetectionRule
class DetectionRuleRepository:
    def __init__(self): self.rules={}
    def create_rule(self, rule): self.rules[rule.id]=rule; return rule
    def get_rule(self, rule_id): return self.rules.get(rule_id)
    def list_rules(self): return list(self.rules.values())
    def update_rule(self, rule_id, **changes):
        rule=self.rules[rule_id]; [setattr(rule,k,v) for k,v in changes.items() if hasattr(rule,k)]; return rule
    def delete_rule(self, rule_id): return self.rules.pop(rule_id,None) is not None
