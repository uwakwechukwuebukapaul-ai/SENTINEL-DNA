import logging

from flask import Flask, abort, jsonify, redirect, render_template_string, request, url_for

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.investigation.reporting import InvestigationReporter
from sentinel_dna.risk.risk_engine import RiskEngine
from sentinel_dna.investigation.analyst_actions import AnalystActionService
from sentinel_dna.config import SentinelDNASettings


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sentinel DNA v1.0 Beta</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 40px;
      background: #0f172a;
      color: #e2e8f0;
    }

    .card {
      background: #111827;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }

    .risk {
      color: #fbbf24;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <h1>Sentinel DNA v1.0 Beta Analyst Workspace</h1>
  <p>Investigations: {{ investigations|length }} · Open: {{ investigations|selectattr('case.status', 'equalto', 'open')|list|length }}</p>

  {% for item in investigations %}
    <section class="card">
      <h2>{{ item.case.title }}</h2>

      <p>{{ item.case.description }}</p>

      <p class="risk">
        Risk: {{ item.risk.level|upper }} {{ item.risk.score }}/100
      </p>

      <p>{{ item.summary.executive_summary }}</p>
      <p>Confidence: {{ item.confidence }} · Status: {{ item.case.status|upper }}</p>
      <p><a href="{{ url_for('detail', case_id=item.case.case_id) }}">Open investigation</a></p>

      <h3>Recommended Actions</h3>

      <ul>
        {% for action in item.summary.recommended_actions %}
          <li>{{ action }}</li>
        {% endfor %}
      </ul>
    </section>
  {% else %}
    <section class="card">
      No cases yet. Run the CLI demo to create a sample investigation.
    </section>
  {% endfor %}
</body>
</html>
"""

DETAIL_PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>{{ case.case_id }}</title>
<style>body{font-family:Arial;margin:40px;background:#0f172a;color:#e2e8f0}.card{background:#111827;border:1px solid #334155;border-radius:12px;padding:18px;margin:14px 0}a{color:#93c5fd}textarea,input,select,button{padding:8px;margin:4px}</style></head>
<body><a href="{{ url_for('index') }}">← Dashboard</a><h1>{{ case.title }}</h1>
<div class="card"><b>Case:</b> {{ case.case_id }} · <b>Severity:</b> {{ case.severity }} · <b>Status:</b> {{ case.status }}<p>{{ case.description }}</p></div>
<div class="card"><h2>Evidence</h2>{% for e in evidence %}<p>{{ e.summary }} — confidence {{ e.confidence }}<br>Indicators: {{ e.indicators|join(', ') }}</p>{% else %}<p>No evidence.</p>{% endfor %}</div>
<div class="card"><h2>Analyst actions</h2><form method="post" action="{{ url_for('action', case_id=case.case_id) }}"><input name="analyst" placeholder="Analyst name" required><select name="action"><option value="confirm_finding">Confirm finding</option><option value="dismiss_finding">Dismiss finding</option><option value="escalate">Escalate</option><option value="add_note">Add note</option></select><textarea name="note" placeholder="Analyst note"></textarea><button>Record action</button></form></div>
<div class="card"><h2>Audit history</h2>{% for event in case.events %}<p>{{ event.timestamp }} · {{ event.event_type }} · {{ event.message }}</p>{% endfor %}</div></body></html>
"""


def create_app(data_dir: str | None = None) -> Flask:
    app = Flask(__name__)
    settings = SentinelDNASettings.from_environment()
    resolved_data_dir = data_dir or settings.data_dir
    # Explicitly keep debug mode off unless an operator opts in for local development.
    app.config.update(JSON_SORT_KEYS=False)
    logger = logging.getLogger("sentinel_dna.web")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
        return response

    @app.get("/healthz")
    def healthz():
        try:
            CaseStore(resolved_data_dir)
            return jsonify({"status": "ok", "service": "sentinel-dna", "version": "1.0-beta"})
        except OSError as exc:
            logger.exception("Health check storage failure")
            return jsonify({"status": "degraded", "service": "sentinel-dna", "error": str(exc)}), 503

    @app.get("/readyz")
    def readyz():
        try:
            CaseStore(resolved_data_dir)
            return jsonify({"status": "ready"})
        except OSError as exc:
            return jsonify({"status": "not_ready", "error": str(exc)}), 503

    @app.get("/")
    def index():
        case_store = CaseStore(resolved_data_dir)
        evidence_engine = EvidenceEngine(resolved_data_dir)
        risk_engine = RiskEngine()
        reporter = InvestigationReporter()

        investigations = []

        for case in case_store.list_cases():
            evidence_items = [
                evidence_engine.get(evidence_id)
                for evidence_id in case.evidence_ids
            ]

            risk = risk_engine.assess(evidence_items)

            summary = reporter.summarize(
                case,
                evidence_items,
                risk,
            )

            investigations.append(
                {
                    "case": case,
                    "risk": risk,
                    "summary": summary,
                    "confidence": "evidence-backed",
                }
            )

        return render_template_string(
            PAGE,
            investigations=investigations,
        )

    @app.get("/investigations/<case_id>")
    def detail(case_id: str):
        case_store = CaseStore(resolved_data_dir)
        evidence_engine = EvidenceEngine(resolved_data_dir)
        try:
            case = case_store.get(case_id)
        except FileNotFoundError:
            abort(404)
        evidence = [evidence_engine.get(evidence_id) for evidence_id in case.evidence_ids]
        return render_template_string(DETAIL_PAGE, case=case, evidence=evidence)

    @app.post("/investigations/<case_id>/actions")
    def action(case_id: str):
        try:
            AnalystActionService(resolved_data_dir).record(
                case_id, request.form.get("action", ""), request.form.get("analyst", ""), request.form.get("note", ""),
            )
        except ValueError as exc:
            abort(400, description=str(exc))
        return redirect(url_for("detail", case_id=case_id))

    return app


if __name__ == "__main__":
    runtime_settings = SentinelDNASettings.from_environment()
    create_app(runtime_settings.data_dir).run(
        host=runtime_settings.host,
        port=runtime_settings.port,
        debug=runtime_settings.debug,
    )
