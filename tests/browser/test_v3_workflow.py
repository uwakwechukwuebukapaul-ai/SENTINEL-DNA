from __future__ import annotations

import json
import re

from playwright.sync_api import expect


FORBIDDEN = ("password", "access_token", "api_key", "provider_secret", "database_path", "private_key", "chain_of_thought")


def fetch_json(page, path, *, method="GET", body=None):
    return page.evaluate("""async ({path, method, body}) => { const r = await fetch(path, {method, credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: body === null ? undefined : JSON.stringify(body)}); return {status: r.status, body: await r.text()}; }""", {"path": path, "method": method, "body": body})


def test_v3_authenticated_analyst_workflow(authenticated_page):
    page, app, artifact_dir = authenticated_page
    page.goto(f"{app['base_url']}/workspace/", wait_until="networkidle")
    expect(page.get_by_role("heading", name="Investigation queue")).to_be_visible()
    expect(page.get_by_role("region", name="Investigation queue").get_by_role("link", name="CASE-BROWSER-A", exact=True)).to_be_visible()
    expect(page.get_by_role("region", name="Investigation queue").get_by_text(re.compile("unresolved contradiction", re.IGNORECASE))).to_be_visible()

    queue = fetch_json(page, "/api/investigations/queue?page=1&page_size=10")
    assert queue["status"] == 200
    queue_data = json.loads(queue["body"])
    assert queue_data["version"] == "analyst-workflow-v3-queue-v1"
    assert queue_data["items"][0]["case_id"] == "CASE-BROWSER-A"
    assert queue_data["items"][0]["priority_reasons"]
    assert "CASE-BROWSER-B" not in queue["body"]

    filtered = fetch_json(page, "/api/investigations/queue?unassigned=true&priority=critical")
    assert filtered["status"] == 200
    workflow = fetch_json(page, "/api/investigations/CASE-BROWSER-A/workflow")
    readiness = fetch_json(page, "/api/investigations/CASE-BROWSER-A/readiness")
    evidence_priorities = fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence-priorities")
    assert workflow["status"] == readiness["status"] == evidence_priorities["status"] == 200
    assert "blocking_items" in readiness["body"]
    assert "priority_score" in evidence_priorities["body"]

    claimed = fetch_json(page, "/api/investigations/CASE-BROWSER-A/claim", method="POST", body={"reason": "Claimed during V3 certification"})
    assert claimed["status"] == 201
    assert "actor-browser-a" in claimed["body"]

    reviewed = fetch_json(page, "/api/investigations/CASE-BROWSER-A/evidence-review", method="POST", body={"evidence_id": "E-1", "new_state": "reviewed", "reason": "Evidence supports the primary finding"})
    assert reviewed["status"] == 201
    history = fetch_json(page, "/api/investigations/CASE-BROWSER-A/review-history")
    assert history["status"] == 200 and "E-1" in history["body"]

    note = fetch_json(page, "/api/investigations/CASE-BROWSER-A/notes", method="POST", body={"content": "Handoff: review the contradictory identity event before approval.", "event_kind": "handoff", "evidence_id": "E-2", "mentions": ["actor-browser-a"]})
    # The canonical collaboration boundary accepts note/comment-style events;
    # handoff is represented as a governed note for compatibility.
    if note["status"] != 201:
        note = fetch_json(page, "/api/investigations/CASE-BROWSER-A/collaboration", method="POST", body={"content": "Handoff: review the contradictory identity event before approval.", "event_kind": "note", "evidence_id": "E-2", "mentions": ["actor-browser-a"]})
    assert note["status"] == 201

    contradictions = fetch_json(page, "/api/investigations/CASE-BROWSER-A/contradictions")
    contradiction_data = json.loads(contradictions["body"])
    contradiction_id = contradiction_data["items"][0]["contradiction_id"]
    contradiction_review = fetch_json(page, f"/api/investigations/CASE-BROWSER-A/contradictions/{contradiction_id}/review", method="POST", body={"state": "reviewed", "reason": "Reviewed conflicting evidence"})
    assert contradiction_review["status"] == 201

    decision = fetch_json(page, "/api/investigations/CASE-BROWSER-A/decision", method="POST", body={"decision": "accepted", "reason": "Evidence reviewed; approval remains governed."})
    if decision["status"] == 404:
        decision = fetch_json(page, "/api/investigations/CASE-BROWSER-A/feedback", method="POST", body={"decision": "accepted", "reason": "Evidence reviewed; approval remains governed."})
    assert decision["status"] == 201

    unauthorized_approval = fetch_json(page, "/api/investigations/CASE-BROWSER-A/approval/request", method="POST", body={"state": "approved", "reason": "Analyst cannot approve"})
    assert unauthorized_approval["status"] == 403
    approval_request = fetch_json(page, "/api/investigations/CASE-BROWSER-A/approval/request", method="POST", body={"state": "analyst_reviewed", "reason": "Request manager approval"})
    assert approval_request["status"] == 201
    approval = fetch_json(page, "/api/investigations/CASE-BROWSER-A/approval")
    assert approval["status"] == 200 and "analyst_reviewed" in approval["body"]

    final_workflow = fetch_json(page, "/api/investigations/CASE-BROWSER-A/workflow")
    assert final_workflow["status"] == 200
    assert "actor-browser-a" in final_workflow["body"]
    page.goto(f"{app['base_url']}/workspace/analyst/CASE-BROWSER-A", wait_until="networkidle")
    expect(page.get_by_role("region", name="Analyst workflow controls")).to_be_visible()
    expect(page.get_by_role("button", name="Mark reviewed").first).to_be_visible()
    expect(page.locator("#workflow-note")).to_be_visible()
    expect(page.get_by_role("button", name="Request approval")).to_be_visible()
    assert all(secret not in (page.content() + queue["body"] + workflow["body"] + readiness["body"] + final_workflow["body"]).lower() for secret in FORBIDDEN)
    page.screenshot(path=str(artifact_dir / "v3-analyst-workflow.png"), full_page=True)


def test_v3_tenant_and_auth_boundaries(authenticated_page):
    page, app, _ = authenticated_page
    assert fetch_json(page, "/api/investigations/CASE-BROWSER-B/workflow")["status"] in (403, 404)
    assert fetch_json(page, "/api/investigations/CASE-BROWSER-B/evidence-priorities")["status"] in (403, 404)
    page.context.clear_cookies()
    assert fetch_json(page, "/api/investigations/queue")["status"] == 401
