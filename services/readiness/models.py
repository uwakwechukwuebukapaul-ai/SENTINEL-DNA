from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
def utc_now() -> str: return datetime.now(timezone.utc).isoformat()
@dataclass
class ReadinessCheck:
    name: str; category: str; passed: bool; details: str = ""; recommendation: str = ""; checked_at: str = field(default_factory=utc_now)
    def public(self) -> dict[str, Any]: return asdict(self)
@dataclass
class ReadinessScore:
    category: str; score: float; passed: int; total: int
    def public(self) -> dict[str, Any]: return asdict(self)
@dataclass
class ReadinessReport:
    checks: list[ReadinessCheck]; scores: list[ReadinessScore]; overall_score: float; ready: bool; environment: str; version: str; startup_timestamp: str; generated_at: str = field(default_factory=utc_now)
    @property
    def failed_checks(self) -> list[ReadinessCheck]: return [check for check in self.checks if not check.passed]
    @property
    def recommendations(self) -> list[str]: return [check.recommendation for check in self.failed_checks if check.recommendation]
    def public(self) -> dict[str, Any]:
        return {"overall_score": self.overall_score, "ready": self.ready, "environment": self.environment, "version": self.version, "startup_timestamp": self.startup_timestamp, "generated_at": self.generated_at, "category_scores": [score.public() for score in self.scores], "passed_checks": [check.public() for check in self.checks if check.passed], "failed_checks": [check.public() for check in self.checks if not check.passed], "recommendations": [check.recommendation for check in self.checks if not check.passed and check.recommendation]}
