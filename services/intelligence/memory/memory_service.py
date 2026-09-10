"""Application services for tenant-safe investigation learning."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable

from services.intelligence.investigation.canonical import sha256_digest

from .models import AnalystFeedbackRecord, InvestigationMemoryRecord
from .repository import InvestigationMemoryRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(max(low, min(high, float(value))), 6)


def _tokens(values: Iterable[Any]) -> set[str]:
    result: set[str] = set()
    for value in values:
        if value is None:
            continue
        result.update(
            token.lower()
            for token in re.findall(r"[a-zA-Z0-9_.-]+", str(value))
            if len(token) > 1
        )
    return result


class MemoryService:
    """Persist investigations and expose deterministic, advisory learning.

    Memory can improve context and confidence signals, but it never changes a
    verdict or authorizes a response. Every tenant-scoped method requires an
    explicit tenant ID; legacy calls remain isolated to the ``default`` tenant.
    """

    def __init__(
        self,
        repository: InvestigationMemoryRepository | None = None,
        feedback_repository: Any | None = None,
    ) -> None:
        self.repository = repository or InvestigationMemoryRepository()
        self.feedback_repository = feedback_repository

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "to_dict"):
            converted = value.to_dict()
            return dict(converted) if isinstance(converted, dict) else {}
        if hasattr(value, "snapshot"):
            converted = value.snapshot()
            return dict(converted) if isinstance(converted, dict) else {}
        return dict(value) if isinstance(value, dict) else dict(vars(value))

    @staticmethod
    def _feature_set(context: dict[str, Any], result: dict[str, Any]) -> set[str]:
        alert = context.get("alert") if isinstance(context.get("alert"), dict) else {}
        features: list[Any] = [
            alert.get("type"), alert.get("category"), alert.get("title"),
            result.get("risk"), result.get("priority"),
        ]
        for item in context.get("artifacts", []) or context.get("evidence", []) or []:
            if isinstance(item, dict):
                features.extend(item.get(key) for key in ("type", "category", "source", "technique", "tactic"))
        for item in result.get("mitre", []) or []:
            features.append(item.get("technique_id") if isinstance(item, dict) else item)
        return _tokens(features)

    @staticmethod
    def attack_pattern_similarity(left: Iterable[Any], right: Iterable[Any]) -> float:
        """Return deterministic Jaccard similarity for attack-pattern tokens."""
        left_tokens, right_tokens = set(left), set(right)
        if not left_tokens and not right_tokens:
            return 1.0
        if not left_tokens or not right_tokens:
            return 0.0
        return _clamp(len(left_tokens & right_tokens) / len(left_tokens | right_tokens))

    @staticmethod
    def _verdict(value: dict[str, Any]) -> str:
        for key in ("verdict", "decision", "risk", "status"):
            candidate = value.get(key)
            if isinstance(candidate, dict):
                candidate = candidate.get("verdict") or candidate.get("severity") or candidate.get("label")
            if candidate not in (None, ""):
                return str(candidate).strip().lower()
        return "unknown"

    def store_investigation_memory(
        self,
        context: Any,
        reasoning_report: Any = None,
        result: Any = None,
        *,
        tenant_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> InvestigationMemoryRecord:
        ctx, rep, outcome = self._data(context), self._data(reasoning_report), self._data(result)
        resolved_tenant = str(tenant_id or ctx.get("tenant_id") or "default").strip()
        if not resolved_tenant:
            raise ValueError("memory_tenant_id_required")
        case_id = str(ctx.get("case_id") or outcome.get("case_id") or "unknown")
        investigation_id = str(ctx.get("investigation_id") or outcome.get("investigation_id") or case_id)
        alert = ctx.get("alert") if isinstance(ctx.get("alert"), dict) else {}
        scenario = str(ctx.get("scenario") or alert.get("type") or alert.get("category") or "security investigation")
        evidence = list(ctx.get("evidence", []) or ctx.get("artifacts", []) or [])
        evidence_ids = sorted(
            str(item.get("evidence_id") or item.get("id"))
            for item in evidence if isinstance(item, dict) and (item.get("evidence_id") or item.get("id"))
        )
        evidence_fingerprint = sha256_digest({"tenant_id": resolved_tenant, "evidence": evidence})
        features = sorted(self._feature_set(ctx, outcome))
        created_at = str(ctx.get("completed_at") or outcome.get("completed_at") or _now())
        record_payload = {
            "tenant_id": resolved_tenant, "investigation_id": investigation_id,
            "case_id": case_id, "scenario": scenario,
            "evidence_fingerprint": evidence_fingerprint,
        }
        memory_id = "MEM-" + hashlib.sha256(
            json.dumps(record_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        confidence_value = outcome.get("confidence")
        if confidence_value is None:
            confidence_value = rep.get("confidence") or 0.0
        try:
            confidence = _clamp(float(confidence_value))
        except (TypeError, ValueError):
            confidence = 0.0
        provenance_data = {
            **(ctx.get("intelligence_provenance") if isinstance(ctx.get("intelligence_provenance"), dict) else {}),
            **(provenance or {}),
            "source": "investigation_result",
            "tenant_id": resolved_tenant,
            "investigation_id": investigation_id,
            "case_id": case_id,
            "evidence_ids": evidence_ids,
            "evidence_fingerprint": evidence_fingerprint,
            "deterministic": True,
        }
        record = InvestigationMemoryRecord(
            memory_id=memory_id,
            tenant_id=resolved_tenant,
            investigation_id=investigation_id,
            case_id=case_id,
            investigation_type="security_investigation",
            scenario=scenario,
            risk_level=str(outcome.get("risk") or "unknown"),
            confidence=confidence,
            evidence_summary={"count": len(evidence), "references": evidence_ids},
            reasoning_summary={"summary": rep.get("summary", ""), "finding_count": len(rep.get("findings", []) or [])},
            mitre_techniques=sorted({str(item.get("technique_id") if isinstance(item, dict) else item) for item in (rep.get("mitre_techniques", []) or outcome.get("mitre", []) or [])}),
            outcome={"status": outcome.get("status", "completed"), "success": outcome.get("success", True)},
            created_at=created_at,
            synthetic_only=bool(ctx.get("synthetic_only", True)),
            provenance=provenance_data,
            verdict=self._verdict(outcome),
            attack_pattern=features,
            evidence_fingerprint=evidence_fingerprint,
            validation_result=str(
                ctx.get("validation_result")
                or (
                    "validated"
                    if str(outcome.get("status") or "completed").lower() in {"completed", "complete", "validated"}
                    and outcome.get("success", True) is not False
                    else "unvalidated"
                )
            ),
        )
        return self.repository.save(record)

    def retrieve_historical_investigations(
        self,
        tenant_id: str,
        *,
        case_id: str | None = None,
        investigation_id: str | None = None,
        limit: int = 100,
    ) -> list[InvestigationMemoryRecord]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("memory_tenant_id_required")
        if case_id is not None:
            return self.repository.get_case_history(tenant_id, case_id, limit=limit)
        records = self.repository.all(tenant_id)
        if investigation_id is None:
            return records[: max(1, int(limit))]
        return [item for item in records if item.investigation_id == str(investigation_id)][: max(1, int(limit))]

    def retrieve_similar_investigations(
        self,
        investigation_type: str,
        scenario: str = "",
        *,
        tenant_id: str = "default",
        attack_pattern: Iterable[Any] = (),
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        records = self.repository.find_similar(
            investigation_type, scenario, tenant_id=str(tenant_id), limit=max(100, int(limit))
        )
        query_features = set(attack_pattern) or _tokens([scenario])
        scored = [
            {
                "record": record,
                "similarity_score": self.attack_pattern_similarity(query_features, record.attack_pattern),
                "provenance": dict(record.provenance),
            }
            for record in records
        ]
        scored.sort(key=lambda item: (-item["similarity_score"], item["record"].memory_id))
        return scored[: max(1, int(limit))]

    def get_case_history(self, case_id: str, tenant_id: str = "default") -> list[InvestigationMemoryRecord]:
        return self.repository.get_case_history(str(tenant_id), str(case_id))

    def compare_previous_verdict(
        self,
        tenant_id: str,
        verdict: str,
        similar: Iterable[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        items = list(similar)
        prior = [item["record"] for item in items if item.get("record") and item["record"].verdict not in ("", "unknown")]
        verdict = str(verdict or "unknown").lower()
        prior_ids = {item.investigation_id for item in prior}
        feedback = [
            item for item in self.repository.list_feedback(str(tenant_id))
            if not prior_ids or item.investigation_id in prior_ids
        ]
        if not prior:
            return {
                "status": "no_history", "agreement": None, "sample_count": 0,
                "feedback_count": len(feedback), "feedback_verdicts": [item.verdict for item in feedback],
                "advisory_only": True, "tenant_id": str(tenant_id),
            }
        weights = [max(0.0, float(item.get("similarity_score", 0.0))) for item in items if item.get("record") in prior]
        agreeing = sum(weight for item, weight in zip(prior, weights) if item.verdict == verdict)
        total = sum(weights)
        agreement = _clamp(agreeing / total) if total else 0.0
        return {
            "status": "reinforced" if agreement >= 0.5 else "conflicted",
            "agreement": agreement,
            "sample_count": len(prior),
            "prior_verdicts": [item.verdict for item in prior],
            "feedback_count": len(feedback),
            "feedback_verdicts": [item.verdict for item in feedback],
            "advisory_only": True,
            "tenant_id": str(tenant_id),
        }

    def confidence_improvement_signals(
        self,
        current_confidence: float | None,
        similar: Iterable[dict[str, Any]],
        comparison: dict[str, Any],
    ) -> dict[str, Any]:
        records = [item["record"] for item in similar if item.get("record")]
        prior = [float(item.confidence) for item in records]
        baseline = _clamp(sum(prior) / len(prior)) if prior else None
        current = _clamp(float(current_confidence)) if current_confidence is not None else None
        delta = _clamp(current - baseline, -1.0, 1.0) if current is not None and baseline is not None else None
        return {
            "status": "improvement_signal" if delta is not None and delta > 0 else ("historical_support" if comparison.get("status") == "reinforced" else "insufficient_history"),
            "prior_confidence_baseline": baseline,
            "current_confidence": current,
            "confidence_delta": delta,
            "sample_count": len(prior),
            "advisory_only": True,
            "tenant_id": comparison.get("tenant_id"),
        }

    def build_learning_context(
        self,
        tenant_id: str,
        *,
        case_id: str,
        alert: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("memory_tenant_id_required")
        context = {"alert": dict(alert or {}), "artifacts": list(artifacts or [])}
        features = sorted(self._feature_set(context, {}))
        scenario = str(alert.get("type") or alert.get("category") or "security investigation")
        similar = self.retrieve_similar_investigations(
            "security_investigation", scenario, tenant_id=tenant_id, attack_pattern=features
        )
        comparison = self.compare_previous_verdict(tenant_id, "unknown", similar)
        return {
            "historical_investigations": [item["record"].to_dict() for item in similar],
            "similarity_scores": [
                {"memory_id": item["record"].memory_id, "score": item["similarity_score"]}
                for item in similar
            ],
            "previous_verdict_comparison": comparison,
            "confidence_improvement_signals": self.confidence_improvement_signals(None, similar, comparison),
            "provenance": {
                "source": "investigation_memory",
                "tenant_id": tenant_id,
                "case_id": str(case_id),
                "feature_tokens": features,
                "advisory_only": True,
                "deterministic": True,
            },
        }

    def finalize_learning_context(
        self,
        tenant_id: str,
        result: Any,
        learning_context: dict[str, Any],
    ) -> dict[str, Any]:
        result_data = self._data(result)
        similar = [
            {"record": InvestigationMemoryRecord(**item), "similarity_score": score.get("score", 0.0)}
            for item, score in zip(
                learning_context.get("historical_investigations", []),
                learning_context.get("similarity_scores", []),
            )
        ]
        comparison = self.compare_previous_verdict(tenant_id, self._verdict(result_data), similar)
        return {
            **learning_context,
            "previous_verdict_comparison": comparison,
            "confidence_improvement_signals": self.confidence_improvement_signals(result_data.get("confidence"), similar, comparison),
        }

    def record_analyst_feedback(
        self,
        *,
        tenant_id: str,
        investigation_id: str,
        analyst_id: str,
        verdict: str,
        feedback_id: str | None = None,
        confidence: float | None = None,
        reason: str = "",
        evidence_references: Iterable[str] = (),
        provenance: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> AnalystFeedbackRecord:
        tenant_id, investigation_id, analyst_id, verdict = map(str, (tenant_id, investigation_id, analyst_id, verdict))
        if not tenant_id or not investigation_id or not analyst_id or not verdict:
            raise ValueError("memory_feedback_identity_required")
        evidence = sorted({str(value) for value in evidence_references})
        payload = {"tenant_id": tenant_id, "investigation_id": investigation_id, "analyst_id": analyst_id, "verdict": verdict, "evidence": evidence}
        resolved_feedback_id = str(feedback_id or "").strip() or (
            "MFB-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]
        )
        record = AnalystFeedbackRecord(
            feedback_id=resolved_feedback_id, tenant_id=tenant_id, investigation_id=investigation_id,
            analyst_id=analyst_id, verdict=verdict, confidence=_clamp(float(confidence)) if confidence is not None else None,
            reason=str(reason)[:2000], evidence_references=evidence,
            provenance={**(provenance or {}), "source": "analyst_feedback", "tenant_id": tenant_id, "investigation_id": investigation_id},
            created_at=str(created_at or _now()),
        )
        return self.repository.save_feedback(record)

    def summarize_patterns(self, tenant_id: str = "default") -> dict[str, Any]:
        records = self.repository.all(str(tenant_id))
        return {
            "count": len(records),
            "risk_levels": {level: sum(record.risk_level == level for record in records) for level in sorted({record.risk_level for record in records})},
            "attack_patterns": sorted({token for record in records for token in record.attack_pattern}),
            "mitre_techniques": sorted({technique for record in records for technique in record.mitre_techniques}),
            "tenant_id": str(tenant_id),
            "advisory_only": True,
        }


InvestigationMemoryService = MemoryService
