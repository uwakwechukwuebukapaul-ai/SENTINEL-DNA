from __future__ import annotations
import sqlite3, time
from datetime import datetime, timezone
from .models import HuntFinding, HuntQuery, HuntResult, HuntStatus
from services.observability import ObservabilityService

class HuntEngine:
    def __init__(self, db_path: str = "soc.db", observer: ObservabilityService | None = None): self.db_path, self.observer = db_path, observer or ObservabilityService()
    def execute(self, query: HuntQuery) -> HuntResult:
        started = time.perf_counter(); result = HuntResult(query=query, status=HuntStatus.RUNNING, created_at=datetime.now(timezone.utc).isoformat())
        self.observer.event("HUNT_STARTED", hunt_id=result.hunt_id, query_type=query.query_type)
        try:
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                findings = []
                needle = query.query.casefold()
                if query.query_type == "ioc":
                    rows = db.execute("SELECT case_id,ioc_type,value FROM iocs WHERE lower(value) LIKE ? LIMIT ?", (f"%{needle}%", query.limit)).fetchall()
                    findings = [HuntFinding("ioc", dict(row)["value"], dict(row)["case_id"], "IOC value matched query") for row in rows]
                elif query.query_type == "evidence":
                    rows = db.execute("SELECT case_id,type,data FROM evidence WHERE lower(data) LIKE ? LIMIT ?", (f"%{needle}%", query.limit)).fetchall()
                    findings = [HuntFinding("evidence", dict(row)["data"], dict(row)["case_id"], "Evidence content matched query") for row in rows]
                else:
                    rows = db.execute("SELECT case_id,title,severity,status FROM cases WHERE lower(title || ' ' || severity || ' ' || status) LIKE ? LIMIT ?", (f"%{needle}%", query.limit)).fetchall()
                    findings = [HuntFinding("behavior", dict(row)["title"], dict(row)["case_id"], "Case behavior matched query") for row in rows]
            result.findings, result.queries_executed = findings, 1; result.status = HuntStatus.COMPLETED
            self.observer.event("HUNT_COMPLETED", hunt_id=result.hunt_id, status=result.status.value, findings_generated=len(findings), queries_executed=1)
        except Exception as exc:
            result.status, result.error = HuntStatus.FAILED, type(exc).__name__
            self.observer.event("HUNT_FAILED", hunt_id=result.hunt_id, status=result.status.value, errors=[type(exc).__name__])
        result.duration_ms = round((time.perf_counter()-started)*1000, 2); return result
