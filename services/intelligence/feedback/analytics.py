"""Derived, tenant-scoped quality analytics for immutable investigator feedback."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from services.intelligence.investigation.analyst_feedback import AnalystDecision, AnalystFeedback


# Preserve the established analytics response contract. New analyst actions
# are valid append-only events, but adding keys to this public aggregate would
# break existing consumers and historical dashboards.
DECISIONS = ("accepted", "rejected", "modified", "false_positive", "escalated")


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
