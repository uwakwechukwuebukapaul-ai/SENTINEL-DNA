"""Durable application job boundary around the frozen investigation service."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol
from uuid import uuid4

INVESTIGATION_JOB, REPORT_JOB, ENRICHMENT_JOB = "investigation", "report_generation", "enrichment"
JOB_STATUSES = {"queued", "running", "completed", "failed"}
def _now() -> str: return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class BackgroundJob:
    job_type: str; tenant_id: str; payload: dict[str, Any]
    def to_dict(self) -> dict[str, Any]: return asdict(self)
@dataclass(frozen=True)
class JobRecord:
    job_id: str; job_type: str; tenant_id: str; user_id: str; payload: dict[str, Any]; status: str; result: dict[str, Any] | None; error: str | None; attempts: int; created_at: str; updated_at: str
class BackgroundJobQueue(Protocol):
    def enqueue(self, job: BackgroundJob) -> str: ...

class JobStore:
    """SQLite control-plane store; swap adapter, not worker contract, for PostgreSQL."""
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.path = Path(data_dir) / "sentinel_dna_jobs.db"; self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, job_type TEXT NOT NULL, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT, error TEXT, attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    def _connect(self):
        db=sqlite3.connect(self.path); db.row_factory=sqlite3.Row; return db
    def enqueue(self, job: BackgroundJob, user_id: str) -> JobRecord:
        if job.job_type not in {INVESTIGATION_JOB, REPORT_JOB, ENRICHMENT_JOB}: raise ValueError("unsupported job type")
        job_id=f"job-{uuid4().hex}"; now=_now()
        with self._connect() as db: db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(job_id,job.job_type,job.tenant_id,user_id,json.dumps(job.payload),"queued",None,None,0,now,now))
        return self.get(job_id, job.tenant_id)
    def get(self, job_id: str, tenant_id: str) -> JobRecord:
        with self._connect() as db: row=db.execute("SELECT * FROM jobs WHERE job_id=? AND tenant_id=?",(job_id,tenant_id)).fetchone()
        if not row: raise PermissionError("job is not available in this tenant")
        d=dict(row); d["payload"]=json.loads(d["payload"]); d["result"]=json.loads(d["result"]) if d["result"] else None; return JobRecord(**d)
    def transition(self, job_id: str, tenant_id: str, expected: str, status: str, result=None, error=None) -> JobRecord:
        if status not in JOB_STATUSES: raise ValueError("invalid job status")
        with self._connect() as db:
            changed=db.execute("UPDATE jobs SET status=?, result=?, error=?, updated_at=? WHERE job_id=? AND tenant_id=? AND status=?",(status,json.dumps(result) if result else None,error,_now(),job_id,tenant_id,expected)).rowcount
        if changed != 1: raise RuntimeError("invalid job transition")
        return self.get(job_id,tenant_id)
    def next_queued(self) -> JobRecord | None:
        with self._connect() as db: row=db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not row: return None
        return self.get(row["job_id"],row["tenant_id"])
    def recover_running(self, max_attempts: int = 3) -> int:
        """Requeue jobs after a worker crash, bounded to prevent retry storms."""
        with self._connect() as db:
            return db.execute("UPDATE jobs SET status='queued', attempts=attempts+1, updated_at=? WHERE status='running' AND attempts < ?",(_now(),max_attempts)).rowcount

class InvestigationWorker:
    """Worker calls the existing TenantInvestigationService; it does not add a runtime."""
    def __init__(self, data_dir: str | Path = "data") -> None: self.store=JobStore(data_dir); self.data_dir=data_dir
    def run_once(self) -> JobRecord | None:
        self.store.recover_running()
        job=self.store.next_queued()
        if not job: return None
        self.store.transition(job.job_id,job.tenant_id,"queued","running")
        try:
            if job.job_type != INVESTIGATION_JOB: raise ValueError("worker implementation not configured for this job type")
            from sentinel_dna.saas.investigation_service import TenantInvestigationService
            result=TenantInvestigationService(self.data_dir).investigate(job.user_id,job.tenant_id,job.payload["case_id"],job.payload["alert"])
            return self.store.transition(job.job_id,job.tenant_id,"running","completed",result=result.to_dict())
        except Exception:
            return self.store.transition(job.job_id,job.tenant_id,"running","failed",error="job_execution_failed")
