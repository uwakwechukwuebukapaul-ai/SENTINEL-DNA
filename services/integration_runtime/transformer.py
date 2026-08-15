class ExchangeTransformer:
    def to_event(self, payload, *, connector_id, tenant_id, event_type="telemetry", exchange_id):
        from .models import DataExchangeEvent
        return DataExchangeEvent(exchange_id, connector_id, tenant_id, event_type, str(payload))
    def normalize(self, payload): return payload if isinstance(payload, dict) else {"raw": payload}
