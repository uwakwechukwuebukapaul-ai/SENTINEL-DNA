"""Deterministic, provider-neutral fusion of normalized gateway observations."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Iterable, Mapping

from app.intelligence.gateway import IOC, IntelligenceObservation


POLICY_VERSION = "fusion-v1"
REPUTATIONS = frozenset({"unknown", "benign", "suspicious", "malicious"})


@dataclass(frozen=True)
class FreshnessPolicy:
    aging_seconds: int = 86400
    stale_seconds: int = 604800


@dataclass(frozen=True)
class FusionResult:
    ioc: IOC
    status: str
    aggregate_reputation: str
    aggregate_confidence: float | None
    observations: tuple[Mapping[str, Any], ...] = ()
    supporting_providers: tuple[str, ...] = ()
    conflicting_providers: tuple[str, ...] = ()
    stale_providers: tuple[str, ...] = ()
    unavailable_providers: tuple[str, ...] = ()
    malware_associations: tuple[str, ...] = ()
    actor_associations: tuple[str, ...] = ()
    campaign_associations: tuple[str, ...] = ()
    attack_techniques: tuple[str, ...] = ()
    infrastructure_relationships: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    provenance: tuple[Mapping[str, Any], ...] = ()
    explanation: str = ""
    policy_version: str = POLICY_VERSION
    fused_at: datetime | None = None
    tenant_id: str | None = None
    investigation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ioc": {"value": self.ioc.value, "type": self.ioc.type.value}, "status": self.status,
                "aggregate_reputation": self.aggregate_reputation, "aggregate_confidence": self.aggregate_confidence,
                "observations": list(self.observations), "supporting_providers": list(self.supporting_providers),
                "conflicting_providers": list(self.conflicting_providers), "stale_providers": list(self.stale_providers),
                "unavailable_providers": list(self.unavailable_providers), "provenance": list(self.provenance),
                "explanation": self.explanation, "policy_version": self.policy_version,
                "fused_at": self.fused_at.isoformat() if self.fused_at else None,
                "tenant_id": self.tenant_id, "investigation_id": self.investigation_id}


def _context_value(context: Any, name: str) -> Any:
    return context.get(name) if isinstance(context, Mapping) else getattr(context, name, None)


class ProviderNeutralFusionEngine:
    """No I/O, no authority mutation, and deterministic for an explicit clock."""

    def __init__(self, freshness: FreshnessPolicy | None = None, policy_version: str = POLICY_VERSION):
        self.freshness = freshness or FreshnessPolicy()
        self.policy_version = policy_version

    def fuse(self, ioc: IOC, observations: Iterable[IntelligenceObservation], context: Any = None,
             current_time: datetime | None = None) -> FusionResult:
        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("current_time must be timezone-aware")
        valid: list[IntelligenceObservation] = []
        unavailable: set[str] = set()
        for item in observations:
            if not isinstance(item, IntelligenceObservation) or item.ioc != ioc or not item.provider.name:
                continue
            valid.append(item)
        # One observation per provider/value/type/time; retain provider provenance.
        unique: dict[tuple[Any, ...], IntelligenceObservation] = {}
        for item in valid:
            key = (item.provider.name, item.ioc.value, item.ioc.type.value, item.reputation,
                   item.source_timestamp or item.retrieved_at, item.provider_record)
            unique.setdefault(key, item)
        valid = list(unique.values())
        fresh: list[IntelligenceObservation] = []
        stale: set[str] = set()
        records: list[dict[str, Any]] = []
        for item in sorted(valid, key=lambda x: (x.provider.name, x.retrieved_at)):
            age = max(0.0, (now - item.retrieved_at).total_seconds())
            state = "STALE" if item.expires_at and now >= item.expires_at or age >= self.freshness.stale_seconds else ("AGING" if age >= self.freshness.aging_seconds else "FRESH")
            if state == "STALE": stale.add(item.provider.name)
            else: fresh.append(item)
            records.append({"provider": item.provider.name, "reputation": item.reputation or "unknown", "freshness": state,
                            "retrieved_at": item.retrieved_at.isoformat(), "confidence": item.confidence,
                            "provider_score": item.malicious_score, "partial": item.partial})
        reps = {str(x.reputation).lower() for x in fresh if str(x.reputation).lower() in REPUTATIONS}
        non_unknown = reps - {"unknown"}
        if not fresh or not non_unknown:
            status = "NO_INTELLIGENCE" if not fresh else "UNKNOWN"
            reputation = "unknown"
        elif len(non_unknown) > 1:
            status = "CONFLICTED"; reputation = "suspicious"
        else:
            reputation = next(iter(non_unknown)); status = reputation.upper()
        providers_by_rep: dict[str, set[str]] = {}
        for item in fresh:
            rep = str(item.reputation).lower()
            if rep in REPUTATIONS and rep != "unknown": providers_by_rep.setdefault(rep, set()).add(item.provider.name)
        supporting = tuple(sorted(providers_by_rep.get(reputation, set())))
        conflicting = tuple(sorted({p for rep, ps in providers_by_rep.items() if rep != reputation for p in ps}))
        confidences = [x.confidence for x in fresh if isinstance(x.confidence, (int, float)) and isfinite(x.confidence)]
        confidence = None if not confidences else round(min(1.0, max(0.0, sum(confidences) / len(confidences))) * (0.75 if conflicting else 1.0), 3)
        explanation = f"{len(supporting)} supporting provider(s), {len(conflicting)} conflicting provider(s), {len(stale)} stale provider(s); policy {self.policy_version}."
        return FusionResult(ioc, status, reputation, confidence, tuple(records), supporting, conflicting, tuple(sorted(stale)), tuple(sorted(unavailable)),
                            tuple(sorted({v for x in fresh for v in x.malware_families})), tuple(sorted({v for x in fresh for v in x.threat_actors})),
                            tuple(sorted({v for x in fresh for v in x.campaigns})), tuple(sorted({v for x in fresh for v in x.attack_techniques})),
                            tuple(sorted({v for x in fresh for v in x.related_infrastructure})), tuple(sorted({v for x in fresh for v in x.tags})),
                            tuple(records), explanation, self.policy_version, now, _context_value(context, "tenant_id"), _context_value(context, "investigation_id"))
