"""Deterministic investigation scale benchmark."""
from __future__ import annotations

import math

from .models import InvestigationScaleBenchmark, ScaleBenchmarkPoint


class InvestigationScaleBenchmarker:
    """Produce replayable p50/p95 estimates for 10, 100, and 1000 cases."""

    DEFAULT_SIZES = (10, 100, 1000)
    TIMING_MODEL = "deterministic-synthetic-v1; no wall-clock or provider calls"

    def __init__(self, *, tenant_id: str = "tenant-proof-scale", sizes: tuple[int, ...] | None = None) -> None:
        self.tenant_id = str(tenant_id).strip()
        self.sizes = tuple(sizes or self.DEFAULT_SIZES)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        rank = max(1, math.ceil(percentile * len(ordered)))
        return round(ordered[rank - 1], 6)

    @staticmethod
    def _latencies(size: int) -> tuple[list[float], list[float]]:
        baseline = [
            round(4.0 + ((index * 17) % 23) * 0.08 + size * 0.002, 6)
            for index in range(size)
        ]
        enhanced = [
            round(item + 0.35 + size * 0.0004 + (index % 5) * 0.01, 6)
            for index, item in enumerate(baseline)
        ]
        return baseline, enhanced

    def run(self) -> InvestigationScaleBenchmark:
        if not self.tenant_id:
            raise ValueError("proof_scale_tenant_id_required")
        if not self.sizes or any(size not in self.DEFAULT_SIZES for size in self.sizes):
            raise ValueError("proof_scale_sizes_must_be_10_100_1000")
        points: list[ScaleBenchmarkPoint] = []
        for size in self.sizes:
            baseline, enhanced = self._latencies(size)
            baseline_memory = round(128.0 + size * 0.42, 6)
            overhead = round(12.0 + size * 0.08, 6)
            enhanced_memory = round(baseline_memory + overhead, 6)
            points.append(
                ScaleBenchmarkPoint(
                    investigation_count=size,
                    baseline_p50_latency_ms=self._percentile(baseline, 0.50),
                    baseline_p95_latency_ms=self._percentile(baseline, 0.95),
                    enhanced_p50_latency_ms=self._percentile(enhanced, 0.50),
                    enhanced_p95_latency_ms=self._percentile(enhanced, 0.95),
                    baseline_memory_kb=baseline_memory,
                    enhanced_memory_kb=enhanced_memory,
                    memory_overhead_kb=overhead,
                    memory_overhead_rate=round(overhead / baseline_memory, 6),
                )
            )
        return InvestigationScaleBenchmark(
            tenant_id=self.tenant_id,
            points=tuple(points),
            timing_model=self.TIMING_MODEL,
        )


__all__ = ["InvestigationScaleBenchmarker"]
