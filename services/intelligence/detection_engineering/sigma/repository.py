class SigmaRuleRepository:
    def __init__(self): self.rules={}
    def save_rule(self,rule): self.rules[rule.rule_id]=rule; return rule
    def get_rule(self,rule_id): return self.rules.get(rule_id)
    def list_rules(self): return list(self.rules.values())
    def search_rules(self,query): return [r for r in self.rules.values() if query.lower() in r.title.lower() or query.lower() in r.description.lower()]
    def delete_rule(self,rule_id): return self.rules.pop(rule_id,None) is not None
