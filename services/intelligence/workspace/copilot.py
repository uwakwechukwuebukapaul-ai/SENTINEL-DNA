class WorkspaceCopilotContext:
    def build(self,context):
        return {"case":context.case,"investigation":context.investigation,"evidence":context.evidence,"threat":context.threat,"timeline":context.timeline,"risk":context.risk,"compliance":context.compliance,"confidence":context.investigation.get("confidence"),"advisory":True,"requires_human_review":True}
