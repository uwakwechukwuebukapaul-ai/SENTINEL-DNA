from uuid import uuid4
from datetime import datetime, timezone
from .models import ConnectorExecution, DataExchangeEvent, ExecutionStatus
from .repository import IntegrationRuntimeRepository
from .executor import ConnectorExecutor
from .transformer import ExchangeTransformer
from .retry import RetryPolicy
from .telemetry import RuntimeTelemetry
class IntegrationRuntimeService:
    def __init__(self, repository=None, audit=None, executor=None):
        self.repository=repository or IntegrationRuntimeRepository(); self.executor=executor or ConnectorExecutor(); self.transformer=ExchangeTransformer(); self.retry=RetryPolicy(); self.telemetry=RuntimeTelemetry(); self.audit=audit
    def execute(self, tenant_id, connector_id, adapter, operation, payload=None):
        execution=ConnectorExecution(str(uuid4()), connector_id, tenant_id, operation); self.repository.save_execution(execution); execution.status=ExecutionStatus.RUNNING; execution.attempts += 1
        try:
            result=self.executor.execute(adapter, operation, payload); execution.status=ExecutionStatus.SUCCESS; self._audit("connector_execution_succeeded", execution); return execution, result
        except Exception as exc:
            execution.status=ExecutionStatus.RETRYING if self.retry.should_retry(execution) else ExecutionStatus.FAILED; execution.error_message=str(exc); self._audit("connector_execution_failed", execution); return execution, None
        finally:
            execution.completed_at=datetime.now(timezone.utc).isoformat(); self.telemetry.record(execution, status=execution.status)
    def receive(self, tenant_id, connector_id, payload, event_type="telemetry"):
        event=DataExchangeEvent(str(uuid4()), connector_id, tenant_id, event_type, str(payload)); self.repository.save_event(event); self._audit("data_exchange_received", tenant_id=tenant_id, connector_id=connector_id, exchange_id=event.exchange_id); return event
    def normalize(self, payload): return self.transformer.normalize(payload)
    def get_execution(self, execution_id, tenant_id): return self.repository.get_execution(execution_id, tenant_id)
    def list_executions(self, tenant_id): return self.repository.list_executions(tenant_id)
    def _audit(self, event, execution=None, **details):
        if execution: details.update(execution_id=execution.execution_id, tenant_id=execution.tenant_id, connector_id=execution.connector_id)
        if self.audit and hasattr(self.audit, "record"): self.audit.record(event, **details)
