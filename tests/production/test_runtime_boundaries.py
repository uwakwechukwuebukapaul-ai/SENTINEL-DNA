def test_canonical_app_reports_dependency_aware_readiness(canonical_authenticated_client):
    response = canonical_authenticated_client.get("/ready")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["operations"] == "ok"


def test_api_errors_are_safe_and_correlated(canonical_authenticated_client):
    response = canonical_authenticated_client.get(
        "/api/does-not-exist",
        headers={"X-Correlation-ID": "release-check-1"},
    )
    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] == "release-check-1"
    payload = response.get_json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "traceback" not in str(payload).lower()


def test_conflicting_tenant_header_fails_closed(canonical_authenticated_client):
    response = canonical_authenticated_client.get(
        "/api/investigations/queue",
        headers={"X-Organization-ID": "tenant-b"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] in {"organization_context_required", "tenant_scope_violation"}


def test_authentication_rate_limiter_is_bounded():
    from services.core.rate_limit import FixedWindowRateLimiter

    limiter = FixedWindowRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("client-a", now=100.0)
    assert limiter.allow("client-a", now=101.0)
    assert not limiter.allow("client-a", now=102.0)
    assert limiter.allow("client-a", now=161.0)
