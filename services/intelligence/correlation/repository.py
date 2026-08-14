class CorrelationRepository:
    def __init__(self): self._signals={}; self._triggers={}
    def save_signal(self, signal): self._signals.setdefault(signal.tenant_id, []).append(signal); return signal
    def list_signals(self, tenant_id): return list(self._signals.get(tenant_id, []))
    def save_trigger(self, trigger): self._triggers.setdefault(trigger.tenant_id, []).append(trigger); return trigger
    def list_triggers(self, tenant_id): return list(self._triggers.get(tenant_id, []))
