class DemoEnvironment:
    def __init__(self, organization_id="demo-enterprise"): self.organization_id = organization_id; self.steps = []
    def run(self, simulate, investigate, respond, report):
        attack = simulate(self.organization_id); self.steps.append("attack_simulation"); analysis = investigate(attack); self.steps.append("ai_investigation"); response = respond(analysis); self.steps.append("response_workflow"); executive_report = report({"attack": attack, "investigation": analysis, "response": response}); self.steps.append("executive_report"); return {"organization_id": self.organization_id, "steps": self.steps, "attack": attack, "investigation": analysis, "response": response, "executive_report": executive_report}
