"""Application service for validated SOC investigation memory."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .models import InvestigationMemoryRecord
from .repository import InvestigationMemoryRepository


class MemoryService:
    def __init__(self, repository: InvestigationMemoryRepository | None = None) -> None:
        self.repository = repository or InvestigationMemoryRepository()

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if value is None: return {}
        if hasattr(value, "to_dict"): return dict(value.to_dict())
        if hasattr(value, "snapshot"): return dict(value.snapshot())
        return dict(value) if isinstance(value, dict) else dict(vars(value))

    def store_investigation_memory(self, context: Any, reasoning_report: Any = None, result: Any = None) -> InvestigationMemoryRecord:
        ctx, rep, outcome = self._data(context), self._data(reasoning_report), self._data(result)
        case_id = str(ctx.get("case_id") or outcome.get("case_id") or "unknown")
        tenant_id = str(ctx.get("tenant_id") or outcome.get("tenant_id") or "") or None
        evidence = list(ctx.get("evidence", []) or [])
        scenario = str(ctx.get("scenario") or ctx.get("alert", {}).get("type") or "security investigation")
        payload = f"{case_id}|{scenario}|{json.dumps(rep, sort_keys=True, default=str)}"
        return self.repository.save(InvestigationMemoryRecord(
            memory_id="MEM-" + hashlib.sha256(payload.encode()).hexdigest()[:20], case_id=case_id, tenant_id=tenant_id,
            investigation_type="security_investigation", scenario=scenario,
            risk_level=str(outcome.get("risk") if isinstance(outcome.get("risk"), str) else (outcome.get("risk") or {}).get("severity", "unknown")),
            confidence=float(outcome.get("confidence") or rep.get("confidence") or 0.0),
            evidence_summary={"count": len(evidence), "references": [str(x.get("id") or x.get("evidence_id")) for x in evidence if isinstance(x, dict)]},
            reasoning_summary={"summary": rep.get("summary", ""), "finding_count": len(rep.get("findings", []) or [])},
            mitre_techniques=list(rep.get("mitre_techniques", []) or outcome.get("mitre", []) or []),
            outcome={"status": outcome.get("status", "completed"), "success": outcome.get("success", True)},
            created_at=datetime.now(timezone.utc).isoformat(), synthetic_only=True))

    def retrieve_similar_investigations(self, investigation_type: str, scenario: str = "", tenant_id: str | None = None) -> list[InvestigationMemoryRecord]:
        return self.repository.find_similar(investigation_type, scenario, tenant_id=tenant_id)

    def get_case_history(self, case_id: str) -> list[InvestigationMemoryRecord]:
        return self.repository.get_case_history(case_id)

    def summarize_patterns(self) -> dict[str, Any]:
        records = self.repository.all()
        return {"count": len(records), "risk_levels": {level: sum(r.risk_level == level for r in records) for level in sorted({r.risk_level for r in records})}, "mitre_techniques": sorted({technique for r in records for technique in r.mitre_techniques}), "synthetic_only": all(r.synthetic_only for r in records)}
