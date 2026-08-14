TACTICS = ["Initial Access", "Credential Access", "Execution", "Persistence", "Privilege Escalation", "Defense Evasion", "Impact"]
class MitreAttackGraph:
    def build(self, stages):
        nodes = [{"id": tactic, "type": "tactic"} for tactic in TACTICS]
        nodes += [{"id": stage.technique_id, "type": "technique", "tactic": stage.tactic, "name": stage.name} for stage in stages]
        edges = [{"from": stages[i-1].technique_id, "to": stage.technique_id, "relationship": "sequence"} for i, stage in enumerate(stages) if i]
        return {"nodes": nodes, "edges": edges}
