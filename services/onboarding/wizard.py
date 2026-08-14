class DeploymentWizard:
    STEPS = ("organization", "user_invitation", "connector_setup", "data_validation", "security_assessment")
    def __init__(self): self.workflows = {}
    def start(self, organization_id): self.workflows[organization_id] = {step: "pending" for step in self.STEPS}; return self.workflows[organization_id]
    def complete(self, organization_id, step):
        if step not in self.STEPS: raise ValueError("invalid_onboarding_step")
        self.workflows.setdefault(organization_id, self.start(organization_id))[step] = "completed"; return self.workflows[organization_id]
