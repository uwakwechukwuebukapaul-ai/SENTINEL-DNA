class ReasoningInvestigationPlanner:
 def plan(self,hypotheses,priority_evidence,attack_paths=None):
  steps=["Validate highest-priority evidence"]
  if hypotheses: steps += list(hypotheses[0].required_validation)
  if attack_paths: steps += ["Review authentication timeline","Map MITRE techniques"]
  return list(dict.fromkeys(steps))
