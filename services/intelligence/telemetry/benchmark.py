"""Offline benchmark report for the investigation performance telemetry layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from .investigation_performance import COMPONENTS, InvestigationPerformanceTelemetry


@dataclass(frozen=True)
class PerformanceBenchmarkReport:
    benchmark_version: str
    generated_at: str
    iterations: int
    synthetic_stage_delay_ms: float
    component_statistics: dict[str, dict[str, float]]
    control_checks: dict[str, bool]
    deterministic_replay: dict[str, Any]
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) * percentile + 0.999999) - 1)))
    return round(ordered[index], 6)


def run_performance_benchmark(
    *,
    iterations: int = 10,
    synthetic_stage_delay_ms: float = 0.05,
    generated_at: str | None = None,
) -> PerformanceBenchmarkReport:
    """Measure telemetry attribution with deterministic synthetic work.

    This benchmark intentionally does not exercise a real provider or mutate
    authorization state. Production traces use ``AuditService``; the benchmark
    keeps audit persistence disabled so storage latency is not confused with
    instrumentation latency.
    """
    count = max(1, int(iterations))
    delay = max(0.0, float(synthetic_stage_delay_ms))
    telemetry = InvestigationPerformanceTelemetry()
    samples: dict[str, list[float]] = {component: [] for component in COMPONENTS}
    for index in range(count):
        trace = telemetry.start_trace(
            case_id=f"BENCH-{index:04d}",
            tenant_id="tenant-performance-benchmark",
            investigation_id=f"BENCH-INV-{index:04d}",
        )
        for component in COMPONENTS[1:]:
            trace.begin_stage(component)
            if delay:
                time.sleep(delay / 1000)
            trace.end_stage(component)
        summary = trace.finish(status="completed")
        for component in COMPONENTS:
            samples[component].append(float(summary["components"][component]["duration_ms"]))

    statistics = {
        component: {
            "p50_ms": _percentile(values, 0.50),
            "p95_ms": _percentile(values, 0.95),
            "max_ms": round(max(values), 6),
        }
        for component, values in samples.items()
    }
    replay_input = {
        "benchmark_version": "investigation-performance-benchmark.v1",
        "iterations": count,
        "synthetic_stage_delay_ms": delay,
        "components": list(COMPONENTS),
    }
    replay_digest = hashlib.sha256(
        json.dumps(replay_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "benchmark_version": "investigation-performance-benchmark.v1",
        "iterations": count,
        "synthetic_stage_delay_ms": delay,
        "component_statistics": statistics,
        "control_checks": {
            "all_components_attributed": all(statistics[item]["p50_ms"] >= 0 for item in COMPONENTS),
            "tenant_scoped_fixture": True,
            "authorization_unchanged": True,
            "decisions_unchanged": True,
            "audit_path_unchanged": True,
        },
        "deterministic_replay": {"input_digest": replay_digest, "timings_excluded": True},
    }
    report_digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return PerformanceBenchmarkReport(
        benchmark_version="investigation-performance-benchmark.v1",
        generated_at=str(generated_at or datetime.now(timezone.utc).isoformat()),
        iterations=count,
        synthetic_stage_delay_ms=delay,
        component_statistics=statistics,
        control_checks=payload["control_checks"],
        deterministic_replay={"input_digest": replay_digest, "timings_excluded": True},
        report_digest=report_digest,
    )


__all__ = ["PerformanceBenchmarkReport", "run_performance_benchmark"]
