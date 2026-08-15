"""Read-only longitudinal analysis of organizational learning snapshots."""
from .organizational_trend import OrganizationalTrend, stable_organizational_trend_id

CLASSIFICATION_ORDER = {"degrading": 0, "persistent": 1, "recurring": 2, "emerging": 3, "improving": 4, "resolving": 5, "resolved": 6, "stable": 7, "mixed": 8, "insufficient_data": 9}


class OrganizationalTrendService:
    def __init__(self, learning_service=None, effectiveness_service=None, feedback_service=None, organizational_learning_service=None, observation_provider=None):
        self.learning_service = learning_service
        self.effectiveness_service = effectiveness_service
        self.feedback_service = feedback_service
        self.organizational_learning_service = organizational_learning_service
        self.observation_provider = observation_provider

    @staticmethod
    def _v(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    @classmethod
    def _refs(cls, rows, key):
        values = []
        for row in rows:
            value = cls._v(row, key, []) if row else []
            values.extend(value if isinstance(value, (list, tuple, set)) else [value])
        return sorted({str(v) for v in values if v not in (None, "")})

    def _source(self, tenant_id, observations):
        if observations is not None:
            return [x for x in observations if self._v(x, "tenant_id", tenant_id) == tenant_id]
        if self.observation_provider:
            return [x for x in self.observation_provider(tenant_id) if self._v(x, "tenant_id", tenant_id) == tenant_id]
        if self.organizational_learning_service:
            return self.organizational_learning_service.derive(tenant_id)
        return []

    def derive(self, tenant_id, observations=None):
        source = self._source(tenant_id, observations)
        rows = sorted(source, key=lambda x: (str(self._v(x, "timestamp", self._v(x, "observed_at", ""))), str(self._v(x, "pattern_type", self._v(x, "trend_type", ""))), str(self._v(x, "organizational_learning_id", self._v(x, "trend_id", "")))))
        groups = {}
        for row in rows:
            kind = self._v(row, "pattern_type", self._v(row, "trend_type", "unknown"))
            groups.setdefault(kind, []).append(row)
        result = []
        for kind, history in sorted(groups.items()):
            states = [str(self._v(x, "classification", "insufficient_data")) for x in history]
            timestamps = [str(self._v(x, "timestamp", self._v(x, "observed_at", ""))) for x in history]
            timestamps_present = all(timestamps) and len(set(timestamps)) > 1
            present = [s not in ("resolved", "resolved_pattern", "absent", "none", "insufficient_data") for s in states]
            if len(history) < 2 or not timestamps_present:
                classification, direction, uncertainty = "insufficient_data", "unknown", ["insufficient_observations" if len(history) < 2 else "insufficient_temporal_span", "missing_historical_snapshots"]
            elif all(present):
                classification, direction, uncertainty = "persistent", "persistent", []
            elif not present[-1] and any(present[:-1]):
                classification = "resolved" if not any(present[-2:]) else "resolving"
                direction, uncertainty = "improving", []
            elif present[-1] and not any(present[:-1]):
                classification, direction, uncertainty = "emerging", "degrading", []
            elif sum(present) >= 2:
                classification, direction, uncertainty = "recurring", "mixed", []
            else:
                classification, direction, uncertainty = "stable", "stable", []
            latest = history[-1]
            source_class = self._v(latest, "classification", "insufficient_data")
            if classification not in {"insufficient_data", "persistent", "recurring", "emerging", "resolving", "resolved"}:
                classification = source_class if source_class in ("improving", "degrading", "stable", "mixed") else "stable"
                direction = classification
            confidence = 0.0 if classification == "insufficient_data" else round(min(1.0, 0.25 + min(len(history), 5) * 0.1 + (0.2 if len(set(states)) == 1 else 0.0)), 6)
            uncertainty = sorted(set(uncertainty + self._v(latest, "uncertainty", []) + (["missing_team_dimension"] if self._v(latest, "organizational_dimension", "unavailable") == "unavailable" else [])))
            result.append(OrganizationalTrend(tenant_id, stable_organizational_trend_id(tenant_id, kind, self._v(latest, "organizational_dimension", "unavailable")), kind, self._v(latest, "title", kind), f"Historical organizational trend for {kind}; observed association does not establish causation.", classification, direction, "high" if classification == "degrading" else "medium" if classification in ("persistent", "recurring") else "low", confidence, uncertainty, {"source": "organizational_trend", "upstream": ["organizational_learning", "learning_effectiveness", "learning_feedback"], "tenant_id": tenant_id}, self._refs(history, "contributing_investigation_ids"), self._refs(history, "contributing_feedback_ids"), self._refs(history, "contributing_learning_ids"), self._refs(history, "contributing_effectiveness_ids"), len(history), f"{timestamps[0]}..{timestamps[-1]}" if timestamps_present else "", timestamps[0] or None, timestamps[-1] or None, states[-2] if len(states) > 1 else None, states[-1] if states else None, self._v(latest, "organizational_dimension", "unavailable"), self._v(latest, "recommended_organizational_focus", "review the evidence-backed organizational trend")))
        if not result:
            result.append(OrganizationalTrend(tenant_id, stable_organizational_trend_id(tenant_id, "insufficient_data"), "insufficient_data", "Insufficient historical organizational data", "No historical organizational snapshots are available.", "insufficient_data", "unknown", "low", 0.0, ["insufficient_observations", "missing_historical_snapshots"], {"source": "organizational_trend", "upstream": ["organizational_learning", "learning_effectiveness", "learning_feedback"], "tenant_id": tenant_id}, [], [], [], [], 0, "", None, None, None, None, "unavailable", "collect historical organizational learning snapshots"))
        return sorted(result, key=lambda x: (CLASSIFICATION_ORDER.get(x.classification, 99), x.trend_type, x.trend_id))
