"""Sentinel DNA SOC Command Center dashboard."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from services.core.application_container import build_container
from services.api.investigations.controller import InvestigationController


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("SENTINEL_DNA_DB_PATH", BASE_DIR / "soc.db")).resolve()

app = Flask(__name__, template_folder="templates")
app.config["JSON_SORT_KEYS"] = False
app.container = build_container()


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Read a bounded dashboard query with a closed connection."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> dict:
    rows = fetch_all(sql, params)
    return rows[0] if rows else {}


def dashboard_payload() -> dict:
    stats = fetch_one("""
        SELECT (SELECT COUNT(*) FROM cases) cases,
               (SELECT COUNT(*) FROM evidence) evidence,
               (SELECT COUNT(*) FROM timeline) timeline,
               (SELECT COUNT(*) FROM iocs) iocs,
               (SELECT COUNT(*) FROM cases WHERE UPPER(severity) IN ('CRITICAL','HIGH')) high_risk_cases,
               (SELECT COUNT(*) FROM cases WHERE UPPER(status) IN ('OPEN','INVESTIGATING','ACTIVE')) active_cases
    """)
    cases = fetch_all("SELECT case_id,title,severity,status,analyst,created FROM cases ORDER BY id DESC LIMIT 12")
    iocs = fetch_all("SELECT case_id,type,value,created FROM iocs ORDER BY id DESC LIMIT 12")
    evidence = fetch_all("SELECT case_id,type,data,created FROM evidence ORDER BY id DESC LIMIT 8")
    timeline = fetch_all("SELECT case_id,event_type,description,actor,created FROM timeline ORDER BY id DESC LIMIT 10")
    actions = fetch_all("SELECT case_id,action,analyst,created FROM analyst_actions ORDER BY id DESC LIMIT 8")
    notes = fetch_all("SELECT case_id,note,analyst,created FROM case_notes ORDER BY id DESC LIMIT 8")
    return {"stats": stats, "cases": cases, "iocs": iocs, "evidence": evidence,
            "timeline": timeline, "actions": actions, "notes": notes}


@app.errorhandler(sqlite3.Error)
def database_error(_error):
    return render_template("error.html", message="Dashboard data is temporarily unavailable."), 503


@app.get("/")
def dashboard():
    try:
        return render_template("dashboard.html", **dashboard_payload())
    except sqlite3.Error:
        raise


@app.get("/api/dashboard")
def dashboard_api():
    return jsonify(dashboard_payload())


@app.get("/api/cases/<case_id>")
def case_api(case_id: str):
    case = fetch_one("SELECT * FROM cases WHERE case_id=?", (case_id,))
    if not case:
        return jsonify({"error": "case_not_found"}), 404
    case["evidence"] = fetch_all("SELECT id,type,data,sha256,created FROM evidence WHERE case_id=? ORDER BY id DESC", (case_id,))
    case["iocs"] = fetch_all("SELECT id,type,value,created FROM iocs WHERE case_id=? ORDER BY id DESC", (case_id,))
    case["timeline"] = fetch_all("SELECT id,event_type,description,actor,created FROM timeline WHERE case_id=? ORDER BY id DESC", (case_id,))
    case["actions"] = fetch_all("SELECT id,action,analyst,created FROM analyst_actions WHERE case_id=? ORDER BY id DESC", (case_id,))
    return jsonify(case)


@app.post("/api/investigations/run")
def run_investigation():
    payload = request.get_json(silent=True) or {}
    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        return jsonify({"error": "case_id_required"}), 400
    case = fetch_one("SELECT case_id,title,severity,description,status FROM cases WHERE case_id=?", (case_id,))
    if not case:
        return jsonify({"error": "case_not_found"}), 404
    artifacts = fetch_all("SELECT type,data,created FROM evidence WHERE case_id=? ORDER BY id", (case_id,))
    alert = {"case_id": case_id, "title": case["title"], "severity": case["severity"], "description": case["description"]}
    result = InvestigationController(app.container.get("investigation_coordinator")).run(artifacts, case_id, alert)
    return jsonify(result)


@app.get("/healthz")
def healthz():
    try:
        fetch_one("SELECT 1 AS ok")
        return jsonify({"status": "ok", "service": "sentinel-dna-dashboard"})
    except sqlite3.Error:
        return jsonify({"status": "degraded"}), 503


@app.get("/readyz")
def readyz():
    return healthz()


if __name__ == "__main__":
    app.run(host=os.getenv("SENTINEL_DNA_HOST", "127.0.0.1"),
            port=int(os.getenv("SENTINEL_DNA_PORT", "5000")), debug=False)
