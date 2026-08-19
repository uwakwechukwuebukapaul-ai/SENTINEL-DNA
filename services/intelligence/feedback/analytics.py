"""Derived, tenant-scoped quality analytics for immutable investigator feedback."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from services.intelligence.investigation.analyst_feedback import AnalystDecision, AnalystFeedback


DECISIONS = tuple(item.value for item in AnalystDecision)
MIN_FEEDBACK_VOLUME = 2
MAX_QUALITY_ITEMS = 100


def _parse_timestamp(value: str | None, field_name: str) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid_{field_name}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"invalid_{field_name}")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class FeedbackAnalytics:
    tenant_id: str
    window: dict[str, str | None]
    total_feedback_events: int
    counts: dict[str, int]
    rates: dict[str, float]
    trends: list[dict[str, Any]]
    by_case: list[dict[str, Any]]
    by_investigation: list[dict[str, Any]]
    signal_basis: str = "analyst_feedback_events"
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FeedbackAnalyticsService:
    """Compute deterministic read-only quality signals from the canonical repository."""

    def __init__(self, repository):
        self.repository = repository

    def summarize(
        self,
        tenant_id: str,
        *,
        start: str | None = None,
        end: str | None = None,
        case_id: str | None = None,
        investigation_id: str | None = None,
        granularity: str = "daily",
        bucket: str | None = None,
    ) -> FeedbackAnalytics:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        granularity = bucket or granularity
        if granularity == "day":
            granularity = "daily"
        elif granularity == "week":
            granularity = "weekly"
        if granularity not in {"daily", "weekly"}:
            raise ValueError("invalid_bucket")
        start_dt = _parse_timestamp(start, "start")
        end_dt = _parse_timestamp(end, "end")
        if start_dt and end_dt and start_dt > end_dt:
            raise ValueError("invalid_time_range")
        records = self.repository.list_for_tenant(
            tenant_id,
            start=start_dt.isoformat() if start_dt else None,
            end=end_dt.isoformat() if end_dt else None,
            case_id=case_id,
            investigation_id=investigation_id,
        )
        counts = Counter(item.decision for item in records)
        total = len(records)
        normalized_counts = {decision: int(counts.get(decision, 0)) for decision in DECISIONS}
        rates = {
            f"{decision}_rate": round(normalized_counts[decision] / total, 6) if total else 0.0
            for decision in DECISIONS
        }
        trends = self._trends(records, granularity)
        by_case = self._group(records, lambda item: item.case_id)
        by_investigation = self._group(records, lambda item: item.investigation_id)
        return FeedbackAnalytics(
            tenant_id=tenant_id,
            window={"start": start_dt.isoformat() if start_dt else None, "end": end_dt.isoformat() if end_dt else None},
            total_feedback_events=total,
            counts=normalized_counts,
            rates=rates,
            trends=trends,
            by_case=by_case,
            by_investigation=by_investigation,
        )

    @staticmethod
    def _group(records: list[AnalystFeedback], key_fn) -> list[dict[str, Any]]:
        grouped: dict[str, Counter] = defaultdict(Counter)
        for item in records:
            grouped[str(key_fn(item))][item.decision] += 1
        return [
            {"id": key, "total_feedback_events": sum(counter.values()), "counts": {decision: int(counter.get(decision, 0)) for decision in DECISIONS}, "latest_feedback_at": max(item.created_at for item in records if str(key_fn(item)) == key)}
            for key, counter in sorted(grouped.items())
        ]

    @staticmethod
    def _trends(records: list[AnalystFeedback], granularity: str) -> list[dict[str, Any]]:
        grouped: dict[str, Counter] = defaultdict(Counter)
        for item in records:
            timestamp = _parse_timestamp(item.created_at, "created_at")
            if timestamp is None:
                continue
            if granularity == "weekly":
                start_of_week = timestamp.date().toordinal() - timestamp.weekday()
                key = datetime.fromordinal(start_of_week).date().isoformat()
            else:
                key = timestamp.date().isoformat()
            grouped[key][item.decision] += 1
        return [
            {"period_start": key, "total_feedback_events": sum(counter.values()), "counts": {decision: int(counter.get(decision, 0)) for decision in DECISIONS}}
            for key, counter in sorted(grouped.items())
        ]

    def evidence_linked_quality(
        self,
        tenant_id: str,
        report: dict[str, Any],
        records: list[AnalystFeedback],
        *,
        decision: str | None = None,
        evidence_type: str | None = None,
        finding_type: str | None = None,
        recommendation_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Project descriptive outcome associations from one authorized report."""
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        if decision and decision not in DECISIONS:
            raise ValueError("invalid_decision")
        if not 1 <= int(limit) <= MAX_QUALITY_ITEMS:
            raise ValueError("invalid_limit")
        selected = [item for item in records if not decision or item.decision == decision]
        report = dict(report or {})
        case_id = str(report.get("case_id") or "")
        investigation_id = str(report.get("investigation_id") or (report.get("metadata") or {}).get("investigation_id") or case_id)

        def mapping(value: Any) -> dict[str, Any]:
            if isinstance(value, dict):
                return value
            if hasattr(value, "to_dict"):
                result = value.to_dict()
                return result if isinstance(result, dict) else {}
            return {}

        def entity(value: Any, *, default_type: str, id_keys: tuple[str, ...], type_keys: tuple[str, ...]) -> dict[str, Any]:
            data = mapping(value)
            raw_id = next((data.get(key) for key in id_keys if data.get(key) is not None), None)
            raw_type = next((data.get(key) for key in type_keys if data.get(key) is not None), None)
            if raw_id is None:
                raw_id = value if isinstance(value, str) else "unknown"
            return {"id": str(raw_id), "type": str(raw_type or default_type)}

        def aggregate(items: list[Any], *, kind: str, type_filter: str | None, id_keys: tuple[str, ...], type_keys: tuple[str, ...]) -> list[dict[str, Any]]:
            values: list[dict[str, Any]] = []
            for item in items:
                descriptor = entity(item, default_type=kind, id_keys=id_keys, type_keys=type_keys)
                if type_filter and descriptor["type"] != type_filter:
                    continue
                item_id = descriptor["id"]
                relevant = selected
                if kind in {"finding", "recommendation"}:
                    target_key = "finding_id" if kind == "finding" else "recommendation_id"
                    relevant = [record for record in selected if not record.to_dict().get(target_key) or str(record.to_dict().get(target_key)) == item_id]
                counts = Counter(record.decision for record in relevant)
                latest = max((record.created_at for record in relevant), default=None)
                total = len(relevant)
                values.append({
                    f"{kind}_id": item_id,
                    f"{kind}_type": descriptor["type"],
                    "feedback_count": total,
                    "accepted_count": int(counts.get("accepted", 0)),
                    "rejected_count": int(counts.get("rejected", 0)),
                    "modified_count": int(counts.get("modified", 0)),
                    "false_positive_count": int(counts.get("false_positive", 0)),
                    "escalated_count": int(counts.get("escalated", 0)),
                    "acceptance_rate": round(counts.get("accepted", 0) / total, 6) if total else 0.0,
                    "modification_rate": round(counts.get("modified", 0) / total, 6) if total else 0.0,
                    "rejection_rate": round(counts.get("rejected", 0) / total, 6) if total else 0.0,
                    "latest_feedback_at": latest,
                    "insufficient_feedback_volume": total < MIN_FEEDBACK_VOLUME,
                    "association_basis": "case_feedback" if kind == "evidence" else "targeted_or_investigation_feedback",
                })
            return sorted(values, key=lambda item: (-item["feedback_count"], item[f"{kind}_type"], item[f"{kind}_id"]))[: int(limit)]

        return {
            "case_id": case_id,
            "investigation_id": investigation_id,
            "feedback_count": len(selected),
            "evidence": aggregate(list(report.get("evidence") or report.get("artifacts") or []), kind="evidence", type_filter=evidence_type, id_keys=("evidence_id", "id", "reference"), type_keys=("evidence_type", "type", "kind")),
            "findings": aggregate(list(report.get("findings") or []), kind="finding", type_filter=finding_type, id_keys=("finding_id", "id"), type_keys=("finding_type", "type", "kind")),
            "recommendations": aggregate(list(report.get("recommendations") or []), kind="recommendation", type_filter=recommendation_type, id_keys=("recommendation_id", "id"), type_keys=("recommendation_type", "type", "category")),
            "minimum_feedback_volume": MIN_FEEDBACK_VOLUME,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "advisory": True,
        }
