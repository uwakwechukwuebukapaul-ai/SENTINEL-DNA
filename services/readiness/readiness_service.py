from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
from .checks import default_checks
from .models import ReadinessReport, ReadinessScore
class ReadinessService:
    def __init__(self, config: dict[str, Any] | None = None, service_lookup=None, startup_timestamp: str | None = None): self.config = config or {}; self.service_lookup = service_lookup; self.startup_timestamp = startup_timestamp or datetime.now(timezone.utc).isoformat()
    def execute(self) -> ReadinessReport:
        checks = default_checks({**self.config, "STARTUP_TIMESTAMP": self.startup_timestamp}, self.service_lookup); categories = {}
        for check in checks: categories.setdefault(check.category, []).append(check)
        scores = [ReadinessScore(category, round(sum(c.passed for c in items) / len(items) * 100, 2), sum(c.passed for c in items), len(items)) for category, items in categories.items()]
        overall = round(sum(check.passed for check in checks) / len(checks) * 100, 2) if checks else 0; return ReadinessReport(checks, scores, overall, overall == 100, self.config.get("ENVIRONMENT", os.getenv("SENTINEL_ENVIRONMENT", "unknown")), self.config.get("VERSION", os.getenv("SENTINEL_VERSION", "unknown")), self.startup_timestamp)
