import os

from flask import Flask, render_template_string

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.investigation.reporting import InvestigationReporter
from sentinel_dna.risk.risk_engine import RiskEngine


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sentinel DNA v0.1</title>
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
  <h1>Sentinel DNA v0.1 Analyst Workspace</h1>

  {% for item in investigations %}
    <section class="card">
      <h2>{{ item.case.title }}</h2>

      <p>{{ item.case.description }}</p>

      <p class="risk">
        Risk: {{ item.risk.level|upper }} {{ item.risk.score }}/100
      </p>

      <p>{{ item.summary.executive_summary }}</p>

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


def create_app(data_dir: str | None = None) -> Flask:
    app = Flask(__name__)
    resolved_data_dir = (
        data_dir
        or os.getenv("SENTINEL_DNA_DATA_DIR", "data")
    )

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
                }
            )

        return render_template_string(
            PAGE,
            investigations=investigations,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)