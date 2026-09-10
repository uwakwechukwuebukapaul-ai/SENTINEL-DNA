"""Durable, single-job investigation worker for the V2.1 foundation.

This component is deliberately a worker primitive, not a scheduler or a new
investigation engine.  It claims one P0.1 durable job and delegates execution
to the canonical InvestigationCoordinator (or an injected adapter in tests).
The optional heartbeat helper is only a lease-renewal companion; the worker
itself remains a separately launchable polling process and is never started by
the Flask application container.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
import inspect
from collections.abc import Mapping
from typing import Any, Callable

from services.intelligence.repository.execution_repository import (
    ExecutionRepository,
    JobLeaseError,
)
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_lifecycle import (
    InvestigationLifecycleState,
)
from services.intelligence.investigation.investigation_snapshot import InvestigationSnapshot, SnapshotIntegrityError
from services.intelligence.reasoning.evidence_sufficiency import (
    EvidenceSufficiencyEvaluator,
    EvidenceSufficiencyResult,
    SufficiencyStatus,
)
from services.intelligence.runtime.investigation_runtime_policy import (
    InvestigationPolicyViolation,
    InvestigationRuntimePolicy,
)
from services.intelligence.runtime.task import Task
from services.intelligence.runtime.provider_follow_up_capability import ProviderFollowUpError


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 256 or any(ord(char) < 32 for char in text):
        raise ValueError(f"{name} is required")
    return text


class RetryableInvestigationError(RuntimeError):
    """Explicit opt-in marker for bounded worker retry."""


class _LeaseHeartbeat:
    """Auxiliary lease-renewal companion for a synchronous investigation call."""

    def __init__(self, worker: "InvestigationWorker", job: InvestigationJob) -> None:
        self.worker = worker
        self.job = job
        self.stop_event = threading.Event()
        self.lost_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        interval = self.worker.heartbeat_interval_seconds
        if interval <= 0:
            return
        self.thread = threading.Thread(
            target=self._run,
            name=f"sentinel-investigation-heartbeat-{self.job.job_id}",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(0.1, self.worker.lease_seconds))

    def _run(self) -> None:
        while not self.stop_event.wait(self.worker.heartbeat_interval_seconds):
            try:
                self.job = self.worker.repository.heartbeat_job(
                    self.job.job_id,
                    self.job.tenant_id,
                    self.worker.service_identity,
                    lease_seconds=self.worker.lease_seconds,
                    now=self.worker.clock(),
                )
                self.worker._audit(
                    self.job,
                    "WORKER_HEARTBEAT",
                    {"lease_seconds": self.worker.lease_seconds},
                )
            except JobLeaseError:
                self.lost_event.set()
                return
            except Exception:
                # A heartbeat failure is fail-closed.  The execution result
                # must not be finalized after an unknown ownership outcome.
                self.lost_event.set()
                return


class InvestigationWorker:
    """Poll and execute one tenant-bound durable investigation job at a time."""

    def __init__(
        self,
        repository: ExecutionRepository,
        *,
        service_identity: str,
        investigate: Callable[[InvestigationJob], Any] | None = None,
        coordinator: Any | None = None,
        sufficiency_evaluator: Any | None = None,
        runtime_policy: InvestigationRuntimePolicy | None = None,
        follow_up: Callable[[InvestigationJob, Task], Any] | None = None,
        task_executor: Any | None = None,
        provider_follow_up_executor: Any | None = None,
        authorize_job: Callable[[InvestigationJob, str], bool] | None = None,
        is_retryable: Callable[[BaseException | None, Any | None], bool] | None = None,
        lease_seconds: int = 60,
        heartbeat_interval_seconds: float | None = None,
        retry_delay_seconds: int = 5,
        poll_interval_seconds: float = 1.0,
        clock: Callable[[], str] = _utc_iso,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(repository, ExecutionRepository):
            raise TypeError("repository must be an ExecutionRepository")
        self.repository = repository
        self.service_identity = _identity(service_identity, "service_identity")
        if investigate is None and coordinator is None:
            raise ValueError("canonical coordinator or investigation adapter is required")
        self.investigate = investigate
        self.coordinator = coordinator
        self.sufficiency_evaluator = sufficiency_evaluator or EvidenceSufficiencyEvaluator()
        self.runtime_policy = runtime_policy or InvestigationRuntimePolicy()
        self.follow_up = follow_up
        self.task_executor = task_executor
        self.provider_follow_up_executor = provider_follow_up_executor
        # Worker authorization is a security boundary.  Missing authorization
        # configuration must deny processing rather than silently becoming an
        # allow-all worker.
        self.authorize_job = authorize_job if callable(authorize_job) else (lambda _job, _identity: False)
        self.is_retryable = is_retryable or (
            lambda error, result: isinstance(error, RetryableInvestigationError)
        )
        self.lease_seconds = int(lease_seconds)
        if self.lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.heartbeat_interval_seconds = (
            max(0.1, self.lease_seconds / 3)
            if heartbeat_interval_seconds is None
            else float(heartbeat_interval_seconds)
        )
        if self.heartbeat_interval_seconds < 0:
            raise ValueError("heartbeat_interval_seconds cannot be negative")
        self.retry_delay_seconds = max(0, int(retry_delay_seconds))
        self.poll_interval_seconds = max(0.0, float(poll_interval_seconds))
        self.clock = clock
        self.sleep = sleep
        self._shutdown = threading.Event()
        self._current_job: InvestigationJob | None = None
        self._shutdown_audited = False
        self._execution_started_at: str | None = None

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown.is_set()

    def request_shutdown(self) -> None:
        """Stop future claims; current work ends at a safe execution boundary."""
        self._shutdown.set()
        if self._current_job is not None and not self._shutdown_audited:
            self._shutdown_audited = True
            self._audit(self._current_job, "WORKER_SHUTDOWN", {"accepting_work": False})

    def run_once(self, *, tenant_id: str | None = None) -> InvestigationJob | None:
        """Recover expired leases, claim at most one job, and process it."""
        if self.shutdown_requested:
            return None

        now = self.clock()
        recovered = self.repository.recover_expired_jobs(now=now)
        for recovered_job in recovered:
            self._audit(
                recovered_job,
                "JOB_RECOVERED",
                {"state": recovered_job.state.value, "attempt": recovered_job.attempts},
            )

        if self.shutdown_requested:
            return None
        job = self.repository.claim_job(
            self.service_identity,
            tenant_id=tenant_id,
            lease_seconds=self.lease_seconds,
            now=self.clock(),
        )
        if job is None:
            return None
        self._current_job = job
        self._audit(job, "WORKER_CLAIMED", {"attempt": job.attempts})
        try:
            return self._process_claimed_job(job)
        finally:
            self._current_job = None

    def run_forever(self, *, tenant_id: str | None = None) -> None:
        """Run the polling loop until a shutdown request is received."""
        while not self.shutdown_requested:
            processed = self.run_once(tenant_id=tenant_id)
            if processed is None and not self.shutdown_requested:
                self.sleep(self.poll_interval_seconds)

    def _process_claimed_job(self, job: InvestigationJob) -> InvestigationJob | None:
        if job.service_identity != self.service_identity:
            return self._block(job, "worker service identity does not match lease")
        if not all((job.tenant_id, job.case_id, job.investigation_id, job.execution_id, job.correlation_id)):
            return self._block(job, "incomplete investigation identity")

        current = self.repository.get_job(job.job_id, job.tenant_id)
        if current is None:
            return None
        if current.cancel_requested:
            return self._cancel(job, "cancellation requested before execution")
        if not self.authorize_job(current, self.service_identity):
            return self._block(job, "worker service identity is not authorized")
        if self.shutdown_requested:
            return self._cancel(job, "worker shutdown before execution")

        try:
            job = self.repository.heartbeat_job(
                job.job_id,
                job.tenant_id,
                self.service_identity,
                lease_seconds=self.lease_seconds,
                now=self.clock(),
            )
            self._audit(job, "WORKER_HEARTBEAT", {"phase": "before_execution"})
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "before_execution"})
            return self.repository.get_job(job.job_id, job.tenant_id)

        self._audit(job, "INVESTIGATION_STARTED", {"attempt": job.attempts})
        self._audit(job, "INVESTIGATION_ITERATION_STARTED", {"iteration": job.iteration, "attempt": job.attempts})
        self._execution_started_at = self.clock()
        heartbeat = _LeaseHeartbeat(self, job)
        heartbeat.start()
        result: Any | None = None
        error: BaseException | None = None
        try:
            result = self._execute_canonical(job)
        except Exception as exc:  # worker boundary converts application failures to durable state
            error = exc
        finally:
            heartbeat.stop()

        if heartbeat.lost_event.is_set():
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "execution"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        if self.repository.get_cancellation_state(job.job_id, job.tenant_id):
            return self._cancel(job, "cancellation requested during execution")
        if error is None and self._result_succeeded(result):
            return self._route_sufficiency(job, result)
        if isinstance(error, ProviderFollowUpError):
            if error.terminal_state == "CANCELLED":
                return self._cancel(job, error.code)
            if error.terminal_state == "TIMED_OUT":
                return self._timeout(job, error.code)
            if error.terminal_state == "ESCALATED":
                self._audit(job, "INVESTIGATION_ESCALATED", {"reason": error.code, "iteration": job.iteration})
                return self._terminal(job, InvestigationLifecycleState.ESCALATED, error.code)
            return self._block(job, error.code)
        return self._fail_or_retry(job, error, result)

    def _execute_canonical(self, job: InvestigationJob) -> Any:
        parent_snapshot = self._load_verified_snapshot(job)
        if parent_snapshot is not None:
            job.replay_snapshot = parent_snapshot
            job.replay_inputs = parent_snapshot.replay_inputs(
                tenant_id=job.tenant_id, case_id=job.case_id,
                actor_id=job.actor_id or self.service_identity, correlation_id=job.correlation_id,
            )
        if job.iteration == 1:
            task = self.repository.get_follow_up_task(job.job_id, job.tenant_id)
            if task is None:
                raise InvestigationPolicyViolation("authorized follow-up task is missing")
            if self.follow_up is not None:
                parameters = inspect.signature(self.follow_up).parameters
                if any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters.values()) or len(parameters) >= 3:
                    return self.follow_up(job, task, parent_snapshot)
                return self.follow_up(job, task)
            if self.provider_follow_up_executor is not None:
                return self.provider_follow_up_executor.execute_follow_up(
                    job, task, parent_snapshot
                )
            if self.task_executor is not None:
                return self.task_executor.execute(task)
            # The coordinator remains the only investigation engine.  The
            # follow-up task contributes only its safe, persisted objective.
            replay = getattr(job, "replay_inputs", {})
            return self.coordinator.investigate(
                case_id=job.case_id,
                alert={**dict(replay.get("alert") or {}), "case_id": job.case_id, "trigger_id": job.trigger_id,
                       "follow_up": {"capability": task.capability, "objective": task.objective,
                                      "required_evidence": list(task.required_evidence)}},
                artifacts=list(replay.get("artifacts") or []), evidence=list(replay.get("evidence") or []),
                iocs=list(replay.get("iocs") or []), timeline=list(replay.get("timeline") or []),
                tenant_id=job.tenant_id,
                actor_id=job.actor_id or self.service_identity,
                correlation_id=job.correlation_id,
                execution_id=job.execution_id,
            )
        if self.investigate is not None:
            return self.investigate(job)
        # This adapter preserves InvestigationCoordinator.investigate(...)
        # and deliberately carries only safe job identity.  Alert intake and
        # payload persistence are later milestones, not worker shortcuts.
        trigger = self.repository.get_trigger(job.trigger_id, job.tenant_id)
        alert = dict(getattr(trigger, "normalized_payload", {}) or {}) if trigger is not None else {}
        alert.update({"case_id": job.case_id, "trigger_id": job.trigger_id})
        return self.coordinator.investigate(
            case_id=job.case_id,
            alert=alert,
            tenant_id=job.tenant_id,
            actor_id=job.actor_id or self.service_identity,
            correlation_id=job.correlation_id,
            execution_id=job.execution_id,
        )

    def _load_verified_snapshot(self, job: InvestigationJob) -> InvestigationSnapshot | None:
        if not job.snapshot_id:
            return None
        snapshot = self.repository.get_snapshot(job.snapshot_id, job.tenant_id)
        if snapshot is None or job.snapshot_digest != snapshot.digest:
            raise SnapshotIntegrityError("durable job snapshot is unavailable or has a digest mismatch")
        snapshot.verify_scope(
            tenant_id=job.tenant_id, case_id=job.case_id,
            actor_id=job.actor_id or self.service_identity, correlation_id=job.correlation_id,
        )
        return snapshot

    @staticmethod
    def _result_mapping(result: Any) -> Mapping[str, Any]:
        if isinstance(result, Mapping):
            return result
        if hasattr(result, "to_dict") and isinstance(result.to_dict(), Mapping):
            return result.to_dict()
        return {key: getattr(result, key, None) for key in ("success", "status", "evidence", "artifacts", "plan", "metadata")}

    def _snapshot(self, job: InvestigationJob, result: Any) -> InvestigationSnapshot:
        data = self._result_mapping(result)
        evidence: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        for item in list(data.get("evidence") or []) + list(data.get("artifacts") or []):
            if not isinstance(item, Mapping):
                continue
            evidence_id = next((item.get(key) for key in ("evidence_id", "evidence_reference", "artifact_id", "reference", "id") if item.get(key)), None)
            if evidence_id and str(evidence_id) not in seen:
                candidate = dict(item)
                candidate.setdefault("evidence_id", str(evidence_id))
                evidence.append(candidate)
                seen.add(str(evidence_id))
        evidence.sort(key=lambda item: str(item.get("evidence_id")))
        trigger = self.repository.get_trigger(job.trigger_id, job.tenant_id)
        alert = dict(getattr(trigger, "normalized_payload", {}) or {}) if trigger is not None else {"trigger_id": job.trigger_id}
        snapshot = InvestigationSnapshot.create(
            case_id=job.case_id, tenant_id=job.tenant_id,
            actor_id=job.actor_id or self.service_identity, correlation_id=job.correlation_id,
            evidence=evidence, artifacts=list(data.get("artifacts") or []), alert=alert,
            iocs=list(data.get("indicators") or data.get("iocs") or []), timeline=list(data.get("timeline") or []),
            plan=data.get("plan") or {},
            provider_observation_references=data.get("provider_observation_references") or [],
        )
        self.repository.save_snapshot(
            snapshot, job_id=job.job_id, execution_id=job.execution_id, iteration=job.iteration,
            parent_snapshot_id=job.snapshot_id if job.iteration == 1 else None,
            service_identity=self.service_identity,
        )
        return snapshot

    def _route_sufficiency(self, job: InvestigationJob, result: Any) -> InvestigationJob | None:
        try:
            if self._execution_started_at is None:
                self._execution_started_at = self.clock()
            self.runtime_policy.enforce_execution(job=job, started_at=self._execution_started_at, now=self.clock())
            if job.iteration == 1:
                task = self.repository.get_follow_up_task(job.job_id, job.tenant_id)
                if task is None or task.iteration != 1 or task.tenant_id != job.tenant_id or task.case_id != job.case_id:
                    raise InvestigationPolicyViolation("follow-up task identity is invalid")
                if task.deadline_at is not None and task.deadline_at.isoformat() < self.clock():
                    return self._timeout(job, "follow-up task deadline exceeded")
            snapshot = self._snapshot(job, result)
            observed = list(self._result_mapping(result).get("evidence") or []) + list(self._result_mapping(result).get("artifacts") or [])
            evaluation = self.sufficiency_evaluator.evaluate(
                result, case_id=job.case_id, investigation_id=job.investigation_id,
                tenant_id=job.tenant_id, correlation_id=job.correlation_id,
                observed_evidence=observed,
            )
            if not isinstance(evaluation, EvidenceSufficiencyResult):
                raise InvestigationPolicyViolation("sufficiency evaluator returned an invalid contract")
            self.repository.save_sufficiency_evaluation(
                evaluation, job_id=job.job_id, iteration=job.iteration,
                service_identity=self.service_identity,
            )
            self._audit(job, "EVIDENCE_GAP_IDENTIFIED", {
                "iteration": job.iteration, "status": evaluation.status.value,
                "evidence_gap_count": len(evaluation.evidence_gaps),
                "input_evidence_digest": evaluation.input_evidence_digest,
            })
            if evaluation.status == SufficiencyStatus.SUFFICIENT:
                self._audit(job, "AUTONOMOUS_STOP", {"reason": "evidence_sufficient", "iteration": job.iteration})
                self._audit(job, "INVESTIGATION_ITERATION_COMPLETED", {"iteration": job.iteration, "status": evaluation.status.value})
                return self._complete(job)
            if evaluation.status == SufficiencyStatus.UNKNOWN:
                self._audit(job, "INVESTIGATION_ESCALATED", {"reason": "evidence_sufficiency_unknown", "iteration": job.iteration})
                self._audit(job, "INVESTIGATION_ITERATION_COMPLETED", {"iteration": job.iteration, "status": evaluation.status.value})
                return self._terminal(job, InvestigationLifecycleState.ESCALATED, "evidence sufficiency is unknown")
            if evaluation.status == SufficiencyStatus.BLOCKED:
                self._audit(job, "INVESTIGATION_ITERATION_COMPLETED", {"iteration": job.iteration, "status": evaluation.status.value})
                return self._block(job, "evidence sufficiency contract failed closed")
            if job.iteration == 1:
                self._audit(job, "AUTONOMOUS_STOP", {"reason": "max_iterations_reached", "iteration": job.iteration})
                self._audit(job, "INVESTIGATION_ITERATION_COMPLETED", {"iteration": job.iteration, "status": evaluation.status.value})
                return self._terminal(job, InvestigationLifecycleState.ESCALATED, "one follow-up cycle was already consumed")
            self._audit(job, "FOLLOW_UP_ELIGIBILITY_EVALUATED", {"eligible": True, "iteration": 1})
            if self.repository.get_cancellation_state(job.job_id, job.tenant_id):
                return self._cancel(job, "cancellation requested before follow-up")
            parent_task_id = f"INITIAL-{job.job_id}"
            result_mapping = self._result_mapping(result)
            known_iocs = result_mapping.get("indicators") or result_mapping.get("iocs")
            if known_iocs is None:
                known_iocs = list((snapshot.iocs if snapshot is not None else ()) or ())
            task = self.runtime_policy.create_follow_up_task(
                job=job, parent_task_id=parent_task_id, sufficiency=evaluation,
                cancellation_requested=bool(self.repository.get_cancellation_state(job.job_id, job.tenant_id)),
                now=self.clock(),
                known_iocs=known_iocs,
            )
            self._audit(job, "FOLLOW_UP_APPROVED", {"task_id": task.task_id, "iteration": 1})
            self.repository.create_follow_up_task(task, job=job, service_identity=self.service_identity)
            return self.repository.schedule_follow_up(
                job.job_id, job.tenant_id, self.service_identity, now=self.clock()
            )
        except InvestigationPolicyViolation as exc:
            if "duration" in str(exc).lower():
                return self._timeout(job, "maximum investigation duration exceeded")
            self._audit(job, "FOLLOW_UP_ELIGIBILITY_EVALUATED", {"eligible": False, "reason": type(exc).__name__, "iteration": job.iteration})
            self._audit(job, "FOLLOW_UP_REJECTED", {"reason": type(exc).__name__, "iteration": job.iteration})
            return self._block(job, "bounded investigation policy rejected the next action")
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "sufficiency"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        except (SnapshotIntegrityError, ValueError, PermissionError) as exc:
            self._audit(job, "FOLLOW_UP_ELIGIBILITY_EVALUATED", {"eligible": False, "reason": type(exc).__name__, "iteration": job.iteration})
            self._audit(job, "FOLLOW_UP_REJECTED", {"reason": type(exc).__name__, "iteration": job.iteration})
            return self._block(job, "bounded investigation policy rejected the next action")
    def _terminal(self, job: InvestigationJob, state: InvestigationLifecycleState, reason: str) -> InvestigationJob | None:
        try:
            return self.repository.transition_job(
                job.job_id, job.tenant_id, state, service_identity=self.service_identity,
                correlation_id=job.correlation_id, reason=reason, require_lease=True, now=self.clock(),
            )
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": state.value.lower()})
            return self.repository.get_job(job.job_id, job.tenant_id)

    def _timeout(self, job: InvestigationJob, reason: str) -> InvestigationJob | None:
        self._audit(job, "INVESTIGATION_TIMEOUT", {"reason": reason, "iteration": job.iteration})
        return self._terminal(job, InvestigationLifecycleState.TIMED_OUT, reason)

    @staticmethod
    def _result_succeeded(result: Any) -> bool:
        if isinstance(result, dict):
            return result.get("success") is True or str(result.get("status", "")).lower() == "completed"
        return getattr(result, "success", False) is True

    def _complete(self, job: InvestigationJob) -> InvestigationJob | None:
        try:
            completed = self.repository.transition_job(
                job.job_id,
                job.tenant_id,
                InvestigationLifecycleState.COMPLETED,
                service_identity=self.service_identity,
                correlation_id=job.correlation_id,
                reason="canonical investigation completed",
                require_lease=True,
                now=self.clock(),
            )
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "completion"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        if completed is not None:
            self._audit(completed, "INVESTIGATION_COMPLETED", {"attempt": completed.attempts})
        return completed

    def _cancel(self, job: InvestigationJob, reason: str) -> InvestigationJob | None:
        try:
            cancelled = self.repository.transition_job(
                job.job_id,
                job.tenant_id,
                InvestigationLifecycleState.CANCELLED,
                service_identity=self.service_identity,
                correlation_id=job.correlation_id,
                reason=reason,
                require_lease=True,
                now=self.clock(),
            )
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "cancellation"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        if cancelled is not None:
            self._audit(cancelled, "INVESTIGATION_CANCELLED", {"reason": reason})
        return cancelled

    def _block(self, job: InvestigationJob, reason: str) -> InvestigationJob | None:
        try:
            blocked = self.repository.transition_job(
                job.job_id,
                job.tenant_id,
                InvestigationLifecycleState.BLOCKED,
                service_identity=self.service_identity,
                correlation_id=job.correlation_id,
                reason=reason,
                require_lease=True,
                now=self.clock(),
            )
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "blocked"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        return blocked

    def _fail_or_retry(
        self,
        job: InvestigationJob,
        error: BaseException | None,
        result: Any | None,
    ) -> InvestigationJob | None:
        retryable = bool(self.is_retryable(error, result))
        failure_code = "retryable_investigation_failure" if retryable else "investigation_failed"
        failure_reason = (
            "canonical investigation raised an approved retryable failure"
            if retryable
            else "canonical investigation failed"
        )
        if error is not None:
            failure_reason = f"{failure_reason}: {type(error).__name__}"[:256]
        self._audit(job, "INVESTIGATION_FAILED", {"retryable": retryable, "failure_code": failure_code})
        if retryable and job.attempts < job.max_attempts:
            try:
                requeued = self.repository.requeue_job(
                    job.job_id,
                    job.tenant_id,
                    self.service_identity,
                    delay_seconds=self.retry_delay_seconds,
                    failure_code=failure_code,
                    failure_reason=failure_reason,
                    reason="bounded retry scheduled",
                    now=self.clock(),
                )
            except JobLeaseError:
                self._audit(job, "WORKER_LEASE_LOST", {"phase": "retry"})
                return self.repository.get_job(job.job_id, job.tenant_id)
            self._audit(requeued, "JOB_REQUEUED", {"available_at": requeued.available_at})
            return requeued
        try:
            failed = self.repository.transition_job(
                job.job_id,
                job.tenant_id,
                InvestigationLifecycleState.FAILED,
                service_identity=self.service_identity,
                correlation_id=job.correlation_id,
                reason=failure_reason,
                failure_code=failure_code,
                failure_reason=failure_reason,
                require_lease=True,
                now=self.clock(),
            )
        except JobLeaseError:
            self._audit(job, "WORKER_LEASE_LOST", {"phase": "failure"})
            return self.repository.get_job(job.job_id, job.tenant_id)
        return failed

    def _audit(self, job: InvestigationJob, event_type: str, metadata: dict[str, Any]) -> None:
        self.repository.record_audit_event(
            tenant_id=job.tenant_id,
            job_id=job.job_id,
            event_type=event_type,
            actor_id=job.actor_id,
            service_identity=self.service_identity,
            correlation_id=job.correlation_id,
            case_id=job.case_id,
            investigation_id=job.investigation_id,
            execution_id=job.execution_id,
            metadata=metadata,
        )


__all__ = ["InvestigationWorker", "RetryableInvestigationError"]
