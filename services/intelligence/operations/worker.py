"""Single-job worker seam; deployers may call it from a future worker runtime."""
from __future__ import annotations

from datetime import datetime, timezone

from .retry_policy import OperationsRetryPolicy
from .queue import DatabaseOperationsQueue


class OperationsEvaluationWorker:
    def __init__(self, operations_service, repository, worker_id: str, retry_policy=None, lease_seconds: int = 300, queue=None):
        self.operations_service = operations_service; self.repository = repository; self.queue = queue or DatabaseOperationsQueue(repository); self.worker_id = str(worker_id); self.retry_policy = retry_policy or OperationsRetryPolicy(); self.lease_seconds = lease_seconds

    def run(self, evaluation_id: str, *, tenant_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        lease = self.queue.claim(evaluation_id=evaluation_id, tenant_id=tenant_id, worker_id=self.worker_id, lease_seconds=self.lease_seconds, now=now)
        if lease is None: return None
        if lease.get("status") in {"completed", "failed", "cancelled", "dead_lettered"}: return lease
        current = self.repository.update(evaluation_id, tenant_id=tenant_id, status="running", policies_checked=lease.get("policies_checked", 0), alerts_created=lease.get("alerts_created", 0), lease_id=lease["lease_id"], worker_id=self.worker_id)
        if current is None: return None
        self._audit("evaluation_leased", tenant_id, evaluation_id, lease)
        try:
            dashboard = self.operations_service.dashboard(tenant_id=tenant_id, actor_id=lease.get("initiator") or "system", now=now)
            checked = len(dashboard.get("policy_status", {}).get("policies", [])) or int(lease.get("policies_checked", 0))
            result = self.repository.update(evaluation_id, tenant_id=tenant_id, status="completed", policies_checked=checked, alerts_created=len(dashboard.get("alerts", [])), completion_summary={"health": dashboard.get("operational_health", {}).get("status", "unknown")}, completed_at=now.isoformat(), lease_id=lease["lease_id"], worker_id=self.worker_id)
            if result is None: return None
            self.repository.release_lease(evaluation_id, tenant_id=tenant_id, worker_id=self.worker_id, lease_id=lease["lease_id"], now=now)
            self._audit("evaluation_completed", tenant_id, evaluation_id, result)
            return result
        except Exception as error:
            decision = self.retry_policy.decide(retry_count=int(lease.get("retry_count", 0)), category=self.retry_policy.classify(error), now=now)
            failure = {"category": decision.category, "reason": decision.reason, "next_attempt_at": decision.next_attempt_at}
            history = list(lease.get("attempt_history", [])); history.append({"attempt": decision.retry_count, "category": decision.category, "at": now.isoformat(), "outcome": "retry_scheduled" if decision.retry else "failed"})
            result = self.repository.update(evaluation_id, tenant_id=tenant_id, status="retry_scheduled" if decision.retry else "failed", policies_checked=lease.get("policies_checked", 0), alerts_created=0, retry_count=decision.retry_count, failure=failure, next_attempt_at=decision.next_attempt_at, attempt_history=history, completed_at=None if decision.retry else now.isoformat(), lease_id=lease["lease_id"], worker_id=self.worker_id)
            self.repository.release_lease(evaluation_id, tenant_id=tenant_id, worker_id=self.worker_id, lease_id=lease["lease_id"], now=now)
            self._audit("evaluation_retried" if decision.retry else "evaluation_failed", tenant_id, evaluation_id, result)
            return result

    def heartbeat(self, evaluation_id: str, *, tenant_id: str, lease_id: str, now=None):
        renewed = self.repository.renew_lease(evaluation_id, tenant_id=tenant_id, worker_id=self.worker_id, lease_id=lease_id, lease_seconds=self.lease_seconds, now=now)
        if renewed: self._audit("evaluation_heartbeat", tenant_id, evaluation_id, {"lease_id": lease_id, "worker_id": self.worker_id})
        return renewed

    def recover_expired(self, *, tenant_id: str, now=None):
        now = now or datetime.now(timezone.utc); recovered = []
        for item in self.repository.list_expired_leases(tenant_id=tenant_id, now=now):
            decision = self.retry_policy.decide(retry_count=int(item.get("retry_count", 0)), category="transient_failure", now=now)
            recovered_item = self.repository.recover_expired_lease(item["evaluation_id"], tenant_id=tenant_id, status="retry_scheduled" if decision.retry else "dead_lettered", failure={"category": "transient_failure", "reason": "expired_worker_lease_recovered", "next_attempt_at": decision.next_attempt_at}, next_attempt_at=decision.next_attempt_at, now=now)
            if recovered_item: self._audit("evaluation_recovered" if decision.retry else "evaluation_dead_lettered", tenant_id, item["evaluation_id"], recovered_item)
            recovered.append(recovered_item)
        return [item for item in recovered if item]

    def _audit(self, event_type, tenant_id, evaluation_id, metadata):
        audit = getattr(getattr(self.operations_service, "read_model", None), "coordinator", None)
        audit = getattr(audit, "audit_service", None)
        if audit:
            safe = {key: metadata.get(key) for key in ("status", "retry_count", "worker_id", "lease_id", "failure", "next_attempt_at") if isinstance(metadata, dict) and key in metadata}
            audit.record("OPERATIONS_" + event_type.upper(), user_id=metadata.get("initiator", "system") if isinstance(metadata, dict) else "system", details={"tenant_id": str(tenant_id), "evaluation_id": str(evaluation_id), **safe})
