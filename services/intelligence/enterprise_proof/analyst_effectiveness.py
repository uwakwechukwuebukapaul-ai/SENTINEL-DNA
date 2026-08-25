"""Deterministic SOC analyst effectiveness benchmark."""
from __future__ import annotations

from statistics import fmean

from services.intelligence.evaluation.evaluation_models import SyntheticSOCScenario, default_synthetic_soc_scenarios
from services.intelligence.evaluation.investigation_evaluator import OperationalAccuracyEvaluator

from .models import AnalystEffectivenessBenchmark, AnalystEffectivenessCase


class AnalystEffectivenessBenchmarker:
    """Compare analyst-facing outcomes without changing authoritative controls."""

    def __init__(self, scenarios: tuple[SyntheticSOCScenario, ...] | None = None) -> None:
        self.scenarios = tuple(scenarios or default_synthetic_soc_scenarios())
        self.evaluator = OperationalAccuracyEvaluator()

    @staticmethod
    def _analyst_confidence(analyst_ground_truth: float, ai_confidence: float) -> float:
        """Model review confidence as a deterministic blend of AI and ground truth."""
        return round((float(analyst_ground_truth) + float(ai_confidence)) / 2.0, 6)

    def run(self) -> AnalystEffectivenessBenchmark:
        if not self.scenarios:
            raise ValueError("proof_analyst_dataset_required")
        tenant_ids = {str(item.tenant_id) for item in self.scenarios}
        if len(tenant_ids) != 1 or not next(iter(tenant_ids), ""):
            raise PermissionError("proof_analyst_dataset_tenant_mismatch")
        cases: list[AnalystEffectivenessCase] = []
        for scenario in self.scenarios:
            evaluation = self.evaluator.evaluate_scenario(scenario)
            baseline = evaluation.observations["baseline"]
            enhanced = evaluation.observations["organizational_memory"]
            expected = scenario.ground_truth.expected_verdict
            recommendation_accepted = enhanced.advisory_verdict == expected
            cases.append(
                AnalystEffectivenessCase(
                    scenario_id=scenario.scenario_id,
                    tenant_id=scenario.tenant_id,
                    baseline_investigation_time_ms=round(baseline.analyst_review_time_ms, 6),
                    enhanced_investigation_time_ms=round(enhanced.analyst_review_time_ms, 6),
                    baseline_ai_confidence=round(baseline.ai_confidence, 6),
                    enhanced_ai_confidence=round(enhanced.ai_confidence, 6),
                    baseline_analyst_confidence=self._analyst_confidence(
                        scenario.ground_truth.analyst_confidence, baseline.ai_confidence
                    ),
                    enhanced_analyst_confidence=self._analyst_confidence(
                        scenario.ground_truth.analyst_confidence, enhanced.ai_confidence
                    ),
                    recommendation_present=bool(enhanced.advisory_verdict),
                    recommendation_accepted=recommendation_accepted,
                    baseline_false_escalation=(
                        baseline.advisory_verdict == "malicious" and expected == "benign"
                    ),
                    enhanced_false_escalation=(
                        enhanced.advisory_verdict == "malicious" and expected == "benign"
                    ),
                    evidence_provenance_preserved=(
                        bool(enhanced.provenance_evidence)
                        and set(enhanced.provenance_evidence).issubset(set(enhanced.evidence))
                    ),
                )
            )
        cases_tuple = tuple(cases)
        baseline_time = fmean(item.baseline_investigation_time_ms for item in cases_tuple)
        enhanced_time = fmean(item.enhanced_investigation_time_ms for item in cases_tuple)
        baseline_confidence = fmean(item.baseline_analyst_confidence for item in cases_tuple)
        enhanced_confidence = fmean(item.enhanced_analyst_confidence for item in cases_tuple)
        baseline_ai_confidence = fmean(item.baseline_ai_confidence for item in cases_tuple)
        enhanced_ai_confidence = fmean(item.enhanced_ai_confidence for item in cases_tuple)
        baseline_false_escalations = sum(item.baseline_false_escalation for item in cases_tuple)
        enhanced_false_escalations = sum(item.enhanced_false_escalation for item in cases_tuple)
        return AnalystEffectivenessBenchmark(
            tenant_id=next(iter(tenant_ids)),
            cases=cases_tuple,
            investigation_time_reduction_ms=round(baseline_time - enhanced_time, 6),
            investigation_time_reduction_rate=round((baseline_time - enhanced_time) / baseline_time, 6),
            analyst_confidence_improvement=round(enhanced_confidence - baseline_confidence, 6),
            ai_confidence_improvement=round(enhanced_ai_confidence - baseline_ai_confidence, 6),
            recommendation_acceptance_rate=round(
                sum(item.recommendation_accepted for item in cases_tuple) / len(cases_tuple), 6
            ),
            false_escalations_baseline=baseline_false_escalations,
            false_escalations_enhanced=enhanced_false_escalations,
            false_escalation_reduction=baseline_false_escalations - enhanced_false_escalations,
            evidence_provenance_preserved=all(item.evidence_provenance_preserved for item in cases_tuple),
        )


__all__ = ["AnalystEffectivenessBenchmarker"]
