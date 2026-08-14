from __future__ import annotations
import time
from services.core.application_container import build_container
from services.core.serialization import serialize
from .generator import CustomerZeroSimulator

class CustomerZeroInvestigationRunner:
    """Demo adapter that delegates entirely to the canonical coordinator."""
    def __init__(self, container=None):
        self.container = container or build_container()
        self.coordinator = self.container.require("investigation_coordinator")
        self.simulator = CustomerZeroSimulator()

    def investigate(self, scenario: str) -> dict:
        payload = self.simulator.api_payload(scenario)
        started = time.perf_counter()
        result = self.coordinator.investigate(**payload)
        output = serialize(result)
        output["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
        output["synthetic_only"] = True
        return output
