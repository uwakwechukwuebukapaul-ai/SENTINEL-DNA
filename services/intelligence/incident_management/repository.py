class IncidentManagementRepository:
    def __init__(self): self.incidents={}; self.timelines={}; self.slas={}; self.closures={}
    def save_incident(self, incident): self.incidents[(incident.tenant_id, incident.incident_id)]=incident; return incident
    def get_incident(self, tenant_id, incident_id): return self.incidents.get((tenant_id, incident_id))
    def add_timeline(self, item): self.timelines.setdefault((item.incident_id,), []).append(item); return item
    def save_sla(self, sla): self.slas[sla.incident_id]=sla; return sla
    def save_closure(self, report): self.closures[(report.tenant_id, report.incident_id)]=report; return report
