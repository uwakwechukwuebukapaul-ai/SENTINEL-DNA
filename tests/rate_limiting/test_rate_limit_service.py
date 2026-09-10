from services.rate_limiting import RateLimitPolicy, RateLimitRequest, RateLimitService


class RecordingBackend:
    def __init__(self):
        self.calls = []

    def allow(self, key, *, limit, window_seconds):
        self.calls.append((key, limit, window_seconds))
        return len(self.calls) == 1


def test_rate_limit_keys_are_dimensioned_and_do_not_store_raw_identity():
    backend = RecordingBackend()
    service = RateLimitService(backend)
    policy = RateLimitPolicy("investigation:start", 2, 60, cost_class="expensive")
    first = RateLimitRequest(
        tenant_id="tenant-a", actor_id="actor-a", ip_address="10.0.0.1",
        endpoint="/api/investigations", operation="start", cost_class="expensive",
    )
    second = RateLimitRequest(
        tenant_id="tenant-b", actor_id="actor-a", ip_address="10.0.0.1",
        endpoint="/api/investigations", operation="start", cost_class="expensive",
    )

    first_decision = service.allow(first, policy)
    second_decision = service.allow(second, policy)

    assert first_decision.allowed is True
    assert second_decision.allowed is False
    assert first_decision.key_hash != second_decision.key_hash
    assert "tenant-a" not in first_decision.key_hash
    assert backend.calls[0][1:] == (2, 60)


def test_invalid_rate_policy_fails_closed():
    import pytest

    with pytest.raises(ValueError):
        RateLimitPolicy("", 1, 60)
    with pytest.raises(ValueError):
        RateLimitPolicy("bad", 0, 60)
