from __future__ import annotations
from customer_zero.scenarios.catalog import SCENARIOS, get_scenario
from .scoring import score_investigation

class InvestigationEvaluator:
    """Evaluate supplied investigation results against synthetic benchmarks."""
    synthetic_only = True

    def evaluate(self, scenario_name: str, result: dict) -> dict:
        expected = get_scenario(scenario_name)
        scored = score_investigation(expected, result or {})
        failures = [name for name, value in scored["metrics"].items() if value < 1.0]
        return {"case_id": expected["case_id"], "scenario": scenario_name, "score": scored["score"], "metrics": scored["metrics"], "failures": failures, "recommendations": [f"Improve {name.replace('_', ' ')}" for name in failures], "synthetic_only": True}

    def evaluate_all(self, results: dict[str, dict]) -> list[dict]:
        return [self.evaluate(name, results.get(name, {})) for name in SCENARIOS]
