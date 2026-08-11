import os

import requests

from sentinel_dna.ai_investigation.investigation_engine import InvestigationSummary
from sentinel_dna.risk.risk_engine import RiskAssessment


class SlackAlert:
    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")

    def format_message(self, summary: InvestigationSummary, risk: RiskAssessment) -> str:
        actions = "\n".join(f"- {action}" for action in summary.recommended_actions)
        return (
            f"Sentinel DNA Investigation: {summary.case_id}\n"
            f"Risk: {risk.level.upper()} ({risk.score}/100)\n"
            f"{summary.executive_summary}\n"
            f"Recommended actions:\n{actions}"
        )

    def send(self, summary: InvestigationSummary, risk: RiskAssessment) -> bool:
        if not self.webhook_url:
            return False
        response = requests.post(self.webhook_url, json={"text": self.format_message(summary, risk)}, timeout=10)
        response.raise_for_status()
        return True

