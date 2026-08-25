"""Benchmark runner for tenant-scoped operational accuracy validation."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .accuracy_metrics import AccuracyMetrics
from .evaluation_models import (
    EvaluationMode,
    OperationalAccuracyValidationReport,
    ScenarioEvaluation,
    SyntheticSOCScenario,
    default_synthetic_soc_scenarios,
)
from .investigation_evaluator import OperationalAccuracyEvaluator


class OperationalAccuracyBenchmarkRunner:
    """Run baseline/investigation-memory/organizational-memory comparisons."""

    def __init__(
        self,
        dataset: Iterable[SyntheticSOCScenario] | None = None,
        *,
        evaluator: OperationalAccuracyEvaluator | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.dataset = tuple(dataset or default_synthetic_soc_scenarios())
        self.evaluator = evaluator or OperationalAccuracyEvaluator()
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    @staticmethod
    def _average(metrics: list[dict[str, Any]], key: str) -> float:
        return round(sum(float(item.get(key, 0.0)) for item in metrics) / max(1, len(metrics)), 6)

    @staticmethod
    def _stable_scenario(scenario: SyntheticSOCScenario) -> dict[str, Any]:
        data = scenario.to_dict()
        for mode in ("baseline", "investigation_memory_delta", "organizational_memory_delta"):
            if isinstance(data.get(mode), dict):
                data[mode] = dict(data[mode])
                data[mode].pop("execution_latency_ms", None)
        return data

    def run(self, *, tenant_id: str | None = None) -> OperationalAccuracyValidationReport:
        if not self.dataset:
            raise ValueError("evaluation_dataset_required")
        expected_tenant = str(tenant_id or self.dataset[0].tenant_id).strip()
        if not expected_tenant:
            raise ValueError("evaluation_tenant_id_required")
        if any(str(item.tenant_id) != expected_tenant for item in self.dataset):
            raise PermissionError("evaluation_dataset_tenant_mismatch")
        evaluations: tuple[ScenarioEvaluation, ...] = tuple(self.evaluator.evaluate_scenario(item) for item in self.dataset)
        modes = (EvaluationMode.BASELINE.value, EvaluationMode.INVESTIGATION_MEMORY.value, EvaluationMode.ORGANIZATIONAL_MEMORY.value)
        aggregate: dict[str, Any] = {}
        for mode in modes:
            metric_rows = [item.metrics[mode] for item in evaluations]
            aggregate[mode] = {
                key: self._average(metric_rows, key)
                for key in metric_rows[0]
                if isinstance(metric_rows[0][key], (int, float))
            }
        aggregate["investigation_memory_improvement"] = {
            key: self._average([item.metrics["investigation_memory_improvement"] for item in evaluations], key)
            for key in evaluations[0].metrics["investigation_memory_improvement"]
        }
        aggregate["organizational_memory_improvement"] = {
            key: self._average([item.metrics["organizational_memory_improvement"] for item in evaluations], key)
            for key in evaluations[0].metrics["organizational_memory_improvement"]
        }
        baseline_latency = float(aggregate[EvaluationMode.BASELINE.value]["execution_latency_ms"])
        investigation_latency = float(aggregate[EvaluationMode.INVESTIGATION_MEMORY.value]["execution_latency_ms"])
        organizational_latency = float(aggregate[EvaluationMode.ORGANIZATIONAL_MEMORY.value]["execution_latency_ms"])
        latency_impact = {
            "baseline_latency_ms": round(baseline_latency, 6),
            "investigation_memory_latency_ms": round(investigation_latency, 6),
            "organizational_memory_latency_ms": round(organizational_latency, 6),
            "investigation_memory_delta_ms": round(investigation_latency - baseline_latency, 6),
            "organizational_memory_delta_ms": round(organizational_latency - baseline_latency, 6),
        }
        safety = {
            key: all(item.safety.get(key, False) for item in evaluations)
            for key in evaluations[0].safety
        }
        safety["tenant_scoped_dataset"] = all(item.tenant_id == expected_tenant for item in evaluations)
        safety["fail_closed_behavior_unchanged"] = safety.get("fail_closed_unchanged", True) if "fail_closed_unchanged" in safety else all(item.safety.get("fail_closed_unchanged", True) for item in evaluations)
        safety["authorization_unchanged"] = all(item.safety.get("authorization_unchanged", False) for item in evaluations)
        safety["verdict_enforcement_unchanged"] = all(item.safety.get("verdict_enforcement_unchanged", False) for item in evaluations)
        safety["tenant_isolation_unchanged"] = all(item.safety.get("tenant_isolation_unchanged", False) for item in evaluations)
        safety["investigation_result_contract_unchanged"] = all(item.safety.get("investigation_result_contract_unchanged", False) for item in evaluations)
        safety["memory_advisory_only"] = all(item.safety.get("memory_advisory_only", False) for item in evaluations)
        org_improvement = aggregate["organizational_memory_improvement"]
        memory_benefit = AccuracyMetrics.memory_benefit_score(org_improvement)
        replay_payload = {
            "version": "operational-accuracy-validation.v1",
            "tenant_id": expected_tenant,
            "dataset": [self._stable_scenario(item) for item in self.dataset],
            "evaluations": [
                {
                    "scenario_id": item.scenario_id,
                    "metrics": {
                        mode: {key: value for key, value in item.metrics[mode].items() if "latency" not in key and "review_time" not in key}
                        for mode in modes
                    },
                    "safety": item.safety,
                }
                for item in evaluations
            ],
        }
        replay_digest = hashlib.sha256(json.dumps(replay_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        report_payload = {
            "report_version": "operational-accuracy-validation.v1",
            "tenant_id": expected_tenant,
            "generated_at": self.generated_at,
            "scenario_count": len(evaluations),
            "scenario_evaluations": [item.to_dict() for item in evaluations],
            "aggregate_metrics": aggregate,
            "memory_benefit_score": memory_benefit,
            "latency_impact": latency_impact,
            "safety_validation": safety,
            "replay_digest": replay_digest,
            "immutable": True,
        }
        report_digest = hashlib.sha256(json.dumps(report_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        return OperationalAccuracyValidationReport(
            report_version="operational-accuracy-validation.v1",
            tenant_id=expected_tenant,
            generated_at=self.generated_at,
            scenario_count=len(evaluations),
            scenario_evaluations=evaluations,
            aggregate_metrics=aggregate,
            memory_benefit_score=memory_benefit,
            latency_impact=latency_impact,
            safety_validation=safety,
            replay_digest=replay_digest,
            report_digest=report_digest,
        )

    def write(self, report: OperationalAccuracyValidationReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"immutable_validation_report_exists: {target}")
        target.write_text(report.to_json(), encoding="utf-8")
        return target


BenchmarkRunner = OperationalAccuracyBenchmarkRunner

__all__ = ["BenchmarkRunner", "OperationalAccuracyBenchmarkRunner"]
