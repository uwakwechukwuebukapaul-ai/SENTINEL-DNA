class PurpleTeamWorkflow:
    def run(self, campaign_runner, validate, investigate, respond, score, campaign):
        attack = campaign_runner(campaign); validation = validate(attack); ai_result = investigate(attack); response = respond(ai_result); performance = score({"attack": attack, "validation": validation, "investigation": ai_result, "response": response}); return {"attack": attack, "validation": validation, "investigation": ai_result, "response": response, "performance": performance}
