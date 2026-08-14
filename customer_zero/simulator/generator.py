from __future__ import annotations
from datetime import datetime, timezone
from customer_zero.scenarios.catalog import get_scenario

class CustomerZeroSimulator:
    """Deterministic, synthetic scenario generator; never executes payloads."""
    synthetic_only = True

    def __init__(self, seed: int = 0):
        self.seed = seed

    def generate(self, name: str) -> dict:
        scenario = get_scenario(name)
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
        scenario["alert"].update({"case_id": scenario["case_id"], "synthetic": True, "timestamp": timestamp})
        for artifact in scenario["artifacts"]:
            artifact.update({"case_id": scenario["case_id"], "synthetic": True, "timestamp": timestamp})
        scenario["synthetic_only"] = True
        scenario["seed"] = self.seed
        return scenario

    def api_payload(self, name: str) -> dict:
        scenario = self.generate(name)
        return {"case_id": scenario["case_id"], "alert": scenario["alert"], "artifacts": scenario["artifacts"]}
