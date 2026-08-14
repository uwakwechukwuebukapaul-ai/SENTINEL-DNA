from uuid import uuid4
class MSSPService:
    def __init__(self): self.providers = {}; self.customers = {}
    def create_provider(self, organization_id, name): self.providers[organization_id] = {"id": organization_id, "name": name, "type": "service_provider"}; return self.providers[organization_id]
    def add_customer(self, provider_id, customer_org_id):
        if provider_id not in self.providers: raise LookupError("provider_not_found")
        self.customers.setdefault(provider_id, set()).add(customer_org_id); return {"provider_id": provider_id, "customer_organization_id": customer_org_id}
    def switch(self, provider_id, customer_org_id):
        if customer_org_id not in self.customers.get(provider_id, set()): raise PermissionError("customer_isolation_denied")
        return {"provider_id": provider_id, "customer_organization_id": customer_org_id}
    def report_scope(self, provider_id, customer_org_id, report):
        self.switch(provider_id, customer_org_id); return {"organization_id": customer_org_id, "report": report}
