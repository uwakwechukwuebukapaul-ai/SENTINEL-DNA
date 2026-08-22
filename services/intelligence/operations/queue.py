"""Provider-neutral queue boundary over the canonical evaluation repository."""
from __future__ import annotations

from typing import Protocol


class OperationsQueue(Protocol):
    def enqueue(self, *, tenant_id: str, evaluation_id: str) -> dict | None: ...
    def claim(self, *, tenant_id: str, evaluation_id: str, worker_id: str, now=None, lease_seconds: int = 300) -> dict | None: ...
    def acknowledge(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields) -> dict | None: ...
    def retry(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields) -> dict | None: ...
    def dead_letter(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields) -> dict | None: ...
    def release(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, now=None) -> bool: ...
    def recover_expired(self, *, tenant_id: str, now=None) -> list[dict]: ...


class DatabaseOperationsQueue:
    """Local durable backend; a Redis/SQS/Celery adapter can implement the same contract."""

    def __init__(self, repository):
        self.repository = repository

    def enqueue(self, *, tenant_id: str, evaluation_id: str):
        return self.repository.get(evaluation_id, tenant_id=tenant_id)

    def claim(self, *, tenant_id: str, evaluation_id: str, worker_id: str, now=None, lease_seconds: int = 300):
        return self.repository.acquire_lease(evaluation_id, tenant_id=tenant_id, worker_id=worker_id, now=now, lease_seconds=lease_seconds)

    def acknowledge(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields):
        fields.setdefault("policies_checked", 0); fields.setdefault("alerts_created", 0)
        return self.repository.update(evaluation_id, tenant_id=tenant_id, worker_id=worker_id, lease_id=lease_id, status="completed", **fields)

    def retry(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields):
        fields.setdefault("policies_checked", 0); fields.setdefault("alerts_created", 0)
        return self.repository.update(evaluation_id, tenant_id=tenant_id, worker_id=worker_id, lease_id=lease_id, status="retry_scheduled", **fields)

    def dead_letter(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, **fields):
        fields.setdefault("policies_checked", 0); fields.setdefault("alerts_created", 0)
        return self.repository.update(evaluation_id, tenant_id=tenant_id, worker_id=worker_id, lease_id=lease_id, status="dead_lettered", **fields)

    def release(self, *, tenant_id: str, evaluation_id: str, worker_id: str, lease_id: str, now=None):
        return self.repository.release_lease(evaluation_id, tenant_id=tenant_id, worker_id=worker_id, lease_id=lease_id, now=now)

    def recover_expired(self, *, tenant_id: str, now=None):
        recovered = []
        for item in self.repository.list_expired_leases(tenant_id=tenant_id, now=now):
            terminal = int(item.get("retry_count", 0)) >= 3
            value = self.repository.recover_expired_lease(item["evaluation_id"], tenant_id=tenant_id, status="dead_lettered" if terminal else "retry_scheduled", failure={"category": "transient_failure", "reason": "expired_worker_lease_recovered"}, now=now)
            if value: recovered.append(value)
        return recovered
