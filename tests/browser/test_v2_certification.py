from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect


FORBIDDEN = ("password", "access_token", "api_key", "authorization", "cookie", "provider_secret", "database_path", "private_key", "chain_of_thought")


def _fetch_json(page, path):
    return page.evaluate("""async (path) => { const response = await fetch(path, {credentials: 'same-origin'}); return {status: response.status, body: await response.text(), contentType: response.headers.get('content-type')}; }""", path)


def test_v2_authenticated_analyst_workflow_and_exports(authenticated_page):
    page, app, artifact_dir = authenticated_page
    console_errors = []
    request_failures = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("requestfailed", lambda request: request_failures.append(request.url))

    expect(page.get_by_role("region", name="Investigation queue").get_by_role("link", name="CASE-BROWSER-A", exact=True)).to_be_visible()
    page.goto(f"{app['base_url']}/workspace/analyst/CASE-BROWSER-A", wait_until="networkidle")
    expect(page.get_by_text("Why Sentinel DNA reached this conclusion")).to_be_visible()
    expect(page.get_by_text("Evidence graph")).to_be_visible()
    expect(page.get_by_text("Contradiction review")).to_be_visible()
    expect(page.get_by_text("Confidence factors")).to_be_visible()
    expect(page.get_by_text("MITRE ATT&CK mapping")).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"^Supporting Factor Suspicious credential access\b", re.IGNORECASE))).to_be_visible()
    # E-1 is rendered in several evidence references across the projection;
    # certify the drill-down inventory link specifically.
    expect(page.get_by_role("link", name="E-1", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"^IOC malicious\.example\b", re.IGNORECASE))).to_be_visible()
    page.screenshot(path=str(artifact_dir / "v2-investigation-workspace.png"), full_page=True)

    graph = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence-graph-workspace")
    graph_projection = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence-graph")
    report = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/report-export-v2")
    pdf = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/report-export-v2/pdf")
    evidence = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence/E-1")
    explainability = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/explainability")
    decision_support = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/decision-support")
    contradictions = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/contradictions")
    comparison = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence-compare?evidence_a=E-1&evidence_b=E-2")
    assert graph["status"] == 200
    assert graph_projection["status"] == 200
    assert report["status"] == 200
    assert pdf["status"] == 200
    assert evidence["status"] == 200
    assert explainability["status"] == 200
    assert decision_support["status"] == 200
    assert contradictions["status"] == 200
    assert comparison["status"] == 200
    assert "application/pdf" in (pdf["contentType"] or "")
    assert "evidence-graph-workspace-v1" in graph["body"]
    assert "evidence-graph-v1" in graph_projection["body"]
    assert "investigation-report-v2" in report["body"]
    assert "evidence-drilldown-v1" in evidence["body"]
    assert "investigation-explainability-v1" in explainability["body"]
    assert "investigation-decision-support-v1" in decision_support["body"]
    assert "investigation-contradictions-v1" in contradictions["body"]
    assert "evidence-comparison-v1" in comparison["body"]
    assert '"destructive_actions":false' in decision_support["body"].replace(" ", "").lower()
    assert all(pattern not in (graph["body"] + graph_projection["body"] + report["body"] + evidence["body"] + explainability["body"] + decision_support["body"] + contradictions["body"] + comparison["body"]).lower() for pattern in FORBIDDEN)
    assert "chain-of-thought" not in page.content().lower()
    assert not request_failures
    assert not console_errors

    review_id = "CASE-BROWSER-A:contradiction:0"
    reviewed = page.evaluate("""async ({path, csrf}) => { const r = await fetch(path, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify({state: 'reviewed', reason: 'Reviewed during certification'})}); return {status: r.status, body: await r.text()}; }""", {"path": f"/api/investigations/CASE-BROWSER-A/contradictions/{review_id}/review", "csrf": (page.evaluate("() => document.cookie") or "")})
    assert reviewed["status"] == 201
    reviewed_projection = _fetch_json(page, "/api/investigations/CASE-BROWSER-A/contradictions")
    assert reviewed_projection["status"] == 200
    assert '"analyst_review_state":"reviewed"' in reviewed_projection["body"].replace(" ", "").lower()

    cross_tenant = _fetch_json(page, "/api/investigations/CASE-BROWSER-B/report-export-v2")
    assert cross_tenant["status"] in (403, 404)
    assert "CASE-BROWSER-B" not in cross_tenant["body"]
    for path in (
        "/api/investigations/CASE-BROWSER-B/evidence/E-1",
        "/api/investigations/CASE-BROWSER-B/explainability",
        "/api/investigations/CASE-BROWSER-B/evidence-graph",
    ):
        denied = _fetch_json(page, path)
        assert denied["status"] in (403, 404)
        assert "CASE-BROWSER-B" not in denied["body"]

    (artifact_dir / "v2-browser-certification.json").write_text(json.dumps({"workspace": "PASS", "graph": "PASS", "report": "PASS", "pdf": "PASS", "cross_tenant": "PASS", "console_errors": console_errors, "request_failures": request_failures}, indent=2), encoding="utf-8")


def test_v2_unauthenticated_and_tenant_boundary(authenticated_page):
    page, app, _ = authenticated_page
    context = page.context
    page.goto(f"{app['base_url']}/api/investigations/CASE-BROWSER-B/evidence-graph", wait_until="networkidle")
    assert page.url.endswith("/api/investigations/CASE-BROWSER-B/evidence-graph")
    assert page.text_content("body") and "CASE-BROWSER-B" not in page.text_content("body")
    context.clear_cookies()
    response = page.goto(f"{app['base_url']}/workspace/analyst/CASE-BROWSER-A", wait_until="networkidle")
    assert response is not None and response.status == 401
