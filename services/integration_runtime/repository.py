class IntegrationRuntimeRepository:
    def __init__(self): self.executions = {}; self.events = {}
    def save_execution(self, execution): self.executions[(execution.tenant_id, execution.execution_id)] = execution; return execution
    def get_execution(self, execution_id, tenant_id): return self.executions.get((tenant_id, execution_id))
    def list_executions(self, tenant_id): return [x for (t, _), x in self.executions.items() if t == tenant_id]
    def save_event(self, event): self.events[(event.tenant_id, event.exchange_id)] = event; return event
    def list_events(self, tenant_id): return [x for (t, _), x in self.events.items() if t == tenant_id]
