class AutomationMemory:
    def __init__(self, repository): self.repository=repository
    def similar(self, tenant_id, incident_type, severity): return [x for x in self.repository.list_experiences(tenant_id) if x.incident_type==incident_type and x.severity==severity]
