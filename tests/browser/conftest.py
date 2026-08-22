from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server


@pytest.fixture
def browser_app(tmp_path_factory):
    """Run the real application against an isolated temporary database."""
    from database.connection import database
    from app import create_app
    from services.intelligence.models.investigation_intelligence import InvestigationIntelligence

    database_path = tmp_path_factory.mktemp("sentinel-browser") / "sentinel-browser.db"
    previous_path = database.database_path
    previous_env = os.environ.get("SENTINEL_DNA_DB_PATH")
    os.environ["SENTINEL_DNA_ENV"] = "development"
    os.environ["SENTINEL_DNA_SECRET_KEY"] = "browser-certification-only-secret-32-chars"
    os.environ["SENTINEL_DNA_DB_PATH"] = str(database_path)
    database.database_path = str(database_path)
    application = create_app()
    application.config.update(TESTING=True, ENVIRONMENT="development", PROPAGATE_EXCEPTIONS=True)

    authority = application.container.require("canonical_authority")
    auth = application.container.require("auth_service")
    users = {}
    for tenant_id, actor_id, username, email in (
        ("tenant-browser-a", "actor-browser-a", "browser-a", "browser-a@example.test"),
        ("tenant-browser-b", "actor-browser-b", "browser-b", "browser-b@example.test"),
    ):
        authority.tenants.create(f"Browser Tenant {tenant_id[-1].upper()}", tenant_id=tenant_id)
        authority.identities.create(email, username, actor_id=actor_id)
        authority.memberships.add(tenant_id, actor_id, "analyst")
        users[tenant_id] = auth.register(
            username,
            email,
            "BrowserPassword123!",
            "analyst",
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        assert auth.authenticate(username, "BrowserPassword123!") is not None, "browser fixture user could not authenticate through AuthService"

    authority.identities.create("browser-admin@example.test", "Browser Administrator", actor_id="actor-browser-admin")
    authority.memberships.add("tenant-browser-a", "actor-browser-admin", "admin")
    users["tenant-browser-a-admin"] = auth.register(
        "browser-admin",
        "browser-admin@example.test",
        "BrowserPassword123!",
        "admin",
        tenant_id="tenant-browser-a",
        actor_id="actor-browser-admin",
    )
    # Registration intentionally cannot self-grant privilege. The browser
    # fixture represents a separately provisioned administrator identity.
    with auth.db.session() as connection:
        connection.execute(
            "UPDATE users SET role='admin' WHERE id=?",
            (users["tenant-browser-a-admin"].id,),
        )

    coordinator = application.container.require("investigation_coordinator")
    for case_id, tenant_id in (("CASE-BROWSER-A", "tenant-browser-a"), ("CASE-BROWSER-B", "tenant-browser-b")):
        intelligence = InvestigationIntelligence(
            findings=[
                {"finding_id": "F-1", "finding": "Suspicious credential access", "evidence_refs": ["E-1"], "confidence": 0.88},
                {"finding_id": "F-2", "finding": "Benign administrative explanation", "evidence_refs": ["E-2"], "confidence": 0.42, "contradiction": True},
            ],
            recommendations=[{"recommendation_id": "R-1", "action": "review_contradictions", "evidence_refs": ["E-1", "E-2"]}],
            risk_score=87,
            risk_severity="high",
            confidence=0.82,
            iocs=[{"value": "malicious.example", "ioc_type": "domain", "provider": "intel-test", "verdict": "malicious", "confidence": 0.9, "evidence_refs": ["E-1"]}],
            mitre_techniques=[{"technique_id": "T1078", "name": "Valid Accounts", "tactic": "Persistence", "confidence": 0.8, "evidence_refs": ["E-1"]}],
            timeline=[{"event_id": "TL-1", "event": "alert", "timestamp": "2026-01-01T10:00:00Z", "evidence_refs": ["E-1"]}],
            metadata={"tenant_id": tenant_id, "investigation_id": case_id},
        )
        coordinator.intelligence_repository.save(case_id, intelligence)
        coordinator.report_repository.save({
            "case_id": case_id,
            "title": "Browser certification investigation",
            "status": "in_progress",
            "confidence": 0.82,
            "decision": "requires_review",
            "evidence": [
                {"evidence_id": "E-1", "type": "endpoint_event", "source": "edr-test", "timestamp": "2026-01-01T10:00:00Z", "confidence": 0.9, "finding_refs": ["F-1"], "ioc_refs": ["malicious.example"], "mitre_refs": ["T1078"], "provenance": {"source": "controlled-test-fixture"}, "integrity": {"status": "verified"}},
                {"evidence_id": "E-2", "type": "identity_event", "source": "identity-test", "timestamp": "2026-01-01T10:05:00Z", "confidence": 0.4, "finding_refs": ["F-2"], "provenance": {"source": "controlled-test-fixture"}, "integrity": {"status": "verified"}},
            ],
            "findings": intelligence.findings,
            "recommendations": intelligence.recommendations,
            "iocs": intelligence.iocs,
            "mitre": intelligence.mitre_techniques,
            "timeline": intelligence.timeline,
            "provider_observations": [{"provider": "intel-test", "status": "AVAILABLE", "confidence": 0.9, "observed_at": "2026-01-01T10:01:00Z"}],
            "metadata": {"tenant_id": tenant_id, "investigation_id": case_id},
            "tenant_context": {"tenant_id": tenant_id},
        })

    server = make_server("127.0.0.1", 0, application, threaded=False)
    thread = threading.Thread(target=server.serve_forever, name="sentinel-browser-certification", daemon=True)
    thread.start()
    yield {"app": application, "base_url": f"http://127.0.0.1:{server.server_port}", "users": users, "cases": {"tenant-browser-a": "CASE-BROWSER-A", "tenant-browser-b": "CASE-BROWSER-B"}}
    server.shutdown()
    thread.join(timeout=5)
    database.database_path = previous_path
    if previous_env is None:
        os.environ.pop("SENTINEL_DNA_DB_PATH", None)
    else:
        os.environ["SENTINEL_DNA_DB_PATH"] = previous_env


@pytest.fixture(scope="session")
def playwright_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        pytest.fail(f"BROWSER_RUNTIME_UNAVAILABLE: Playwright is not installed ({exc})")
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.fail(f"BROWSER_RUNTIME_UNAVAILABLE: Chromium could not launch ({type(exc).__name__})")
        yield browser
        browser.close()


@pytest.fixture
def authenticated_page(playwright_browser, browser_app, tmp_path):
    context = playwright_browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.goto(f"{browser_app['base_url']}/login", wait_until="networkidle")
    page.locator("input[name='username']").fill("browser-a")
    page.locator("#login-password").fill("BrowserPassword123!")
    with page.expect_response("**/login") as login_response:
        page.get_by_role("button", name="Sign in").click()
    assert login_response.value.status == 302
    page.goto(f"{browser_app['base_url']}/workspace/", wait_until="networkidle")
    assert page.url.endswith("/workspace/")
    yield page, browser_app, tmp_path
    context.close()


@pytest.fixture
def admin_authenticated_page(playwright_browser, browser_app, tmp_path):
    context = playwright_browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.goto(f"{browser_app['base_url']}/login", wait_until="networkidle")
    page.locator("input[name='username']").fill("browser-admin")
    page.locator("#login-password").fill("BrowserPassword123!")
    with page.expect_response("**/login") as login_response:
        page.get_by_role("button", name="Sign in").click()
    assert login_response.value.status == 302
    yield page, browser_app, tmp_path
    context.close()
