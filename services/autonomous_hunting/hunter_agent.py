"""
Autonomous Hunter Agent compatibility layer.

Provides the AutonomousHunterAgent interface expected by
the Sentinel DNA application container.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .hypothesis_engine import HypothesisEngine


@dataclass
class AutonomousHunterAgent:
    """
    AI threat hunting agent foundation.

    Responsible for:
    - generating hunting hypotheses
    - coordinating hunt execution
    - collecting findings
    - producing explainable outputs

    Production actions remain controlled by governance layers.
    """

    name: str = "Autonomous Hunter Agent"
    confidence: float = 0.0
    hypothesis_engine: HypothesisEngine = field(
        default_factory=HypothesisEngine
    )

    findings: List[Dict[str, Any]] = field(default_factory=list)

    def create_hypothesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        hypothesis = self.hypothesis_engine.generate(context)

        return {
            "agent": self.name,
            "hypothesis": hypothesis,
            "confidence": self.confidence,
            "status": "generated",
        }

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = self.create_hypothesis(context)

        self.findings.append(result)

        return result

    def get_findings(self) -> List[Dict[str, Any]]:
        return self.findings