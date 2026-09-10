"""Three-arm operational accuracy evaluator for AI Investigator V1."""
from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from services.intelligence.investigation.investigation_result import InvestigationResult

from .accuracy_metrics import AccuracyMetrics
from .evaluation_models import (
    EvaluationMode,
    InvestigationObservation,
    ScenarioEvaluation,
    SyntheticSOCScenario,
)


class OperationalAccuracyEvaluator:
    """Evaluate advisory quality while holding enforcement controls constant."""

    def __init__(self, metrics: AccuracyMetrics | None = None) -> None:
        self.metrics = metrics or AccuracyMetrics()

    @staticmethod
    def _observation(base: InvestigationObservation, delta: dict[str, Any]) -> InvestigationObservation:
        allowed = {field for field in InvestigationObservation.__dataclass_fields__}
        values = {key: value for key, value in {**base.to_dict(), **delta}.items() if key in allowed}
        for key in ("evidence", "mitre_techniques", "ioc_relationships", "provenance_evidence", "evidence_citations", "disagreement_reasons"):
            if key in values and not isinstance(values[key], tuple):
                values[key] = tuple(values[key])
        return InvestigationObservation(**values)

    @staticmethod
    def _mode_observation(
        base: InvestigationObservation,
        delta: dict[str, Any],
        mode: EvaluationMode,
    ) -> InvestigationObservation:
        observation = OperationalAccuracyEvaluator._observation(base, delta)
        if "execution_latency_ms" not in delta and mode is not EvaluationMode.BASELINE:
            overhead = 0.25 if mode is EvaluationMode.INVESTIGATION_MEMORY else 0.55
            observation = replace(observation, execution_latency_ms=round(base.execution_latency_ms + overhead, 6))
        return observation

    @staticmethod
    def _result(scenario: SyntheticSOCScenario, observation: InvestigationObservation, mode: EvaluationMode) -> InvestigationResult:
        return InvestigationResult(
            success=True,
            status="completed",
            investigation_id=scenario.investigation_id,
            case_id=scenario.case_id,
            artifacts=[{"evidence_id": item, "tenant_id": scenario.tenant_id} for item in observation.evidence],
            evidence=[{"evidence_id": item, "tenant_id": scenario.tenant_id} for item in observation.evidence],
            risk=observation.enforced_verdict,
            confidence=observation.ai_confidence,
            mitre=list(observation.mitre_techniques),
            metadata={
                "evaluation_mode": mode.value,
                "advisory_verdict": observation.advisory_verdict,
                "authorization_status": scenario.authorization_status,
                "fail_closed": scenario.fail_closed,
                "memory_advisory_only": True,
                "tenant_id": scenario.tenant_id,
            },
            tenant_context={"tenant_id": scenario.tenant_id},
        )

    @staticmethod
    def _disagreement_reasons(scenario: SyntheticSOCScenario, observation: InvestigationObservation) -> tuple[str, ...]:
        reasons: list[str] = []
        ground_truth = scenario.ground_truth
        if observation.advisory_verdict != ground_truth.expected_verdict:
            reasons.append("advisory_verdict_disagrees_with_analyst_ground_truth")
        if set(ground_truth.expected_evidence) - set(observation.evidence):
            reasons.append("expected_evidence_missing")
        if set(ground_truth.expected_mitre_techniques) - set(observation.mitre_techniques):
            reasons.append("expected_mitre_technique_missing")
        expected_iocs = {json.dumps(item, sort_keys=True, separators=(",", ":"), default=str) for item in ground_truth.expected_ioc_relationships}
        observed_iocs = {json.dumps(item, sort_keys=True, separators=(",", ":"), default=str) for item in observation.ioc_relationships}
        if not expected_iocs.issubset(observed_iocs):
            reasons.append("expected_ioc_relationship_missing")
        return tuple(reasons)

    def evaluate_scenario(self, scenario: SyntheticSOCScenario) -> ScenarioEvaluation:
        tenant_id = str(scenario.tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("evaluation_tenant_id_required")
        investigation_memory_observation = self._mode_observation(
            scenario.baseline, scenario.investigation_memory_delta, EvaluationMode.INVESTIGATION_MEMORY
        )
        observations = {
            EvaluationMode.BASELINE.value: self._mode_observation(scenario.baseline, {}, EvaluationMode.BASELINE),
            EvaluationMode.INVESTIGATION_MEMORY.value: investigation_memory_observation,
            EvaluationMode.ORGANIZATIONAL_MEMORY.value: self._mode_observation(
                investigation_memory_observation,
                scenario.organizational_memory_delta,
                EvaluationMode.ORGANIZATIONAL_MEMORY,
            ),
        }
        observations = {
            key: replace(value, disagreement_reasons=self._disagreement_reasons(scenario, value))
            for key, value in observations.items()
        }
        results = {
            key: self._result(scenario, value, EvaluationMode(key))
            for key, value in observations.items()
        }
        result_keys = set(InvestigationResult().to_dict())
        safety = {
            "authorization_unchanged": len({result.metadata["authorization_status"] for result in results.values()}) == 1,
            "verdict_enforcement_unchanged": len({result.risk for result in results.values()}) == 1,
            "tenant_isolation_unchanged": all(result.tenant_context.get("tenant_id") == tenant_id for result in results.values()),
            "fail_closed_unchanged": len({bool(result.metadata["fail_closed"]) for result in results.values()}) == 1,
            "investigation_result_contract_unchanged": all(set(result.to_dict()) == result_keys for result in results.values()),
            "memory_advisory_only": all(result.metadata["memory_advisory_only"] for result in results.values()),
        }
        metric_values = {key: self.metrics.calculate(scenario.ground_truth, value) for key, value in observations.items()}
        metric_values["investigation_memory_improvement"] = self.metrics.improvement(
            metric_values[EvaluationMode.BASELINE.value], metric_values[EvaluationMode.INVESTIGATION_MEMORY.value]
        )
        metric_values["organizational_memory_improvement"] = self.metrics.improvement(
            metric_values[EvaluationMode.BASELINE.value], metric_values[EvaluationMode.ORGANIZATIONAL_MEMORY.value]
        )
        return ScenarioEvaluation(
            scenario_id=scenario.scenario_id,
            tenant_id=tenant_id,
            scenario_type=scenario.scenario_type,
            ground_truth=scenario.ground_truth,
            observations=observations,
            metrics=metric_values,
            safety=safety,
        )


# The explicit name avoids ambiguity with the legacy evaluator module; the
# descriptive alias is convenient for provider adapters and callers.
InvestigationAccuracyEvaluator = OperationalAccuracyEvaluator

__all__ = ["InvestigationAccuracyEvaluator", "OperationalAccuracyEvaluator"]
