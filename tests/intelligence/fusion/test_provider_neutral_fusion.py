from datetime import datetime, timedelta, timezone

from app.intelligence.gateway import IOC, IOCType, IntelligenceObservation, ProviderIdentity
from services.intelligence.fusion import ProviderNeutralFusionEngine


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
IOC_VALUE = IOC("example.test", IOCType.DOMAIN)


def obs(provider, reputation, *, retrieved=NOW, confidence=.8):
    return IntelligenceObservation(IOC_VALUE, ProviderIdentity(provider), retrieved, reputation=reputation, confidence=confidence)


def test_agreement_and_provenance_are_deterministic():
    engine = ProviderNeutralFusionEngine()
    result = engine.fuse(IOC_VALUE, [obs("a", "malicious"), obs("b", "malicious")], {"tenant_id": "t"}, NOW)
    assert result.status == "MALICIOUS"
    assert result.supporting_providers == ("a", "b")
    assert result.tenant_id == "t"
    assert result.to_dict() == engine.fuse(IOC_VALUE, [obs("a", "malicious"), obs("b", "malicious")], {"tenant_id": "t"}, NOW).to_dict()


def test_conflict_is_preserved_and_stale_is_visible():
    engine = ProviderNeutralFusionEngine()
    result = engine.fuse(IOC_VALUE, [obs("a", "malicious"), obs("b", "benign", retrieved=NOW - timedelta(days=8))], current_time=NOW)
    assert result.status == "MALICIOUS"
    assert result.stale_providers == ("b",)
    assert result.conflicting_providers == ()


def test_material_disagreement_is_conflicted():
    result = ProviderNeutralFusionEngine().fuse(IOC_VALUE, [obs("a", "malicious"), obs("b", "benign")], current_time=NOW)
    assert result.status == "CONFLICTED"
    assert set(result.conflicting_providers) == {"a", "b"}


def test_zero_and_unknown_results_never_manufacture_reputation():
    engine = ProviderNeutralFusionEngine()
    assert engine.fuse(IOC_VALUE, [], current_time=NOW).status == "NO_INTELLIGENCE"
    assert engine.fuse(IOC_VALUE, [obs("a", "unknown")], current_time=NOW).aggregate_reputation == "unknown"


def test_duplicate_same_provider_does_not_count_twice():
    result = ProviderNeutralFusionEngine().fuse(IOC_VALUE, [obs("a", "malicious"), obs("a", "malicious")], current_time=NOW)
    assert result.supporting_providers == ("a",)
