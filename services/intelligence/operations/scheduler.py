"""Synchronous scheduler seam for future job-runner integration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from .worker import OperationsEvaluationWorker


class OperationsEvaluationScheduler(Protocol):
    def evaluate(self, *, tenant_id: str, actor_id: str, now=None) -> dict: ...
    def dispatch_due_jobs(self, *, tenant_id: str, actor_id: str, now=None) -> list[dict]: ...


class DeterministicOperationsEvaluationScheduler:
    """Evaluate one tenant on demand; no worker, queue, or second pipeline is introduced."""
    def __init__(self, operations_service, repository, queue=None):
        self.operations_service = operations_service
        self.repository = repository
        from .queue import DatabaseOperationsQueue
        self.queue = queue or DatabaseOperationsQueue(repository)

    def enqueue(self, *, tenant_id: str, actor_id: str, now=None):
        started = (now or datetime.now(timezone.utc)).isoformat()
        policies = self.operations_service.policy_service.policies(tenant_id)
        event = self.repository.append(tenant_id=tenant_id, status="queued", policies_checked=len(policies), policy_refs=[item["rule"] for item in policies], initiator=actor_id, started_at=started)
        self.queue.enqueue(tenant_id=tenant_id, evaluation_id=event["evaluation_id"])
        return event

    def evaluate(self, *, tenant_id: str, actor_id: str, now=None):
        run = self.enqueue(tenant_id=tenant_id, actor_id=actor_id, now=now)
        return OperationsEvaluationWorker(self.operations_service, self.repository, worker_id=f"sync-{actor_id}", queue=self.queue).run(run["evaluation_id"], tenant_id=tenant_id, now=now)

    def dispatch_due_jobs(self, *, tenant_id: str, actor_id: str, now=None):
        now = now or datetime.now(timezone.utc); worker = OperationsEvaluationWorker(self.operations_service, self.repository, worker_id=f"dispatch-{actor_id}", queue=self.queue)
        results = []
        runs = self.repository.list_dispatchable(tenant_id=tenant_id, now=now, limit=100) if callable(getattr(self.repository, "list_dispatchable", None)) else self.repository.list_for_tenant(tenant_id=tenant_id)
        for run in runs:
            if run.get("status") in {"queued", "retry_scheduled", "retrying"} and (not run.get("next_attempt_at") or run["next_attempt_at"] <= now.isoformat()):
                result = worker.run(run["evaluation_id"], tenant_id=tenant_id, now=now)
                if result: results.append(result)
        return results

    def recover_expired_jobs(self, *, tenant_id: str, actor_id: str, now=None):
        return OperationsEvaluationWorker(self.operations_service, self.repository, worker_id=f"recovery-{actor_id}").recover_expired(tenant_id=tenant_id, now=now)
