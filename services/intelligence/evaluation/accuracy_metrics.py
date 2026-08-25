"""Pure, deterministic metrics for AI investigation accuracy validation."""
from __future__ import annotations

import json
from typing import Any, Iterable

from .evaluation_models import AnalystGroundTruth, InvestigationObservation


def _set(values: Iterable[Any]) -> set[str]:
    return {str(value) for value in values}


def _relationship_set(values: Iterable[dict[str, Any]]) -> set[str]:
    return {json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str) for value in values}


def _recall(expected: set[str], observed: set[str]) -> float:
    if not expected:
        return 1.0 if not observed else 0.0
    return round(len(expected & observed) / len(expected), 6)


class AccuracyMetrics:
    """Stateless metrics; no metric can authorize or enforce a verdict."""

    @staticmethod
    def calculate(ground_truth: AnalystGroundTruth, observation: InvestigationObservation) -> dict[str, float | int]:
        expected_evidence = _set(ground_truth.expected_evidence)
        observed_evidence = _set(observation.evidence)
        expected_mitre = _set(ground_truth.expected_mitre_techniques)
        observed_mitre = _set(observation.mitre_techniques)
        expected_iocs = _relationship_set(ground_truth.expected_ioc_relationships)
        observed_iocs = _relationship_set(observation.ioc_relationships)
        false_positive = int(ground_truth.expected_verdict == "benign" and observation.advisory_verdict == "malicious")
        false_negative = int(ground_truth.expected_verdict == "malicious" and observation.advisory_verdict == "benign")
        return {
            "verdict_agreement": float(observation.advisory_verdict == ground_truth.expected_verdict),
            "false_positive_count": false_positive,
            "false_negative_count": false_negative,
            "evidence_relevance": _recall(expected_evidence, observed_evidence),
            "mitre_mapping_accuracy": _recall(expected_mitre, observed_mitre),
            "ioc_relationship_accuracy": _recall(expected_iocs, observed_iocs),
            "confidence_calibration": round(max(0.0, 1.0 - abs(float(observation.ai_confidence) - float(ground_truth.analyst_confidence))), 6),
            "uncertainty_score": round(float(observation.uncertainty_score), 6),
            "reasoning_completeness": round(float(observation.reasoning_completeness), 6),
            "provenance_coverage": _recall(expected_evidence, _set(observation.provenance_evidence)),
            "evidence_citation_coverage": _recall(expected_evidence, _set(observation.evidence_citations)),
            "analyst_review_time_ms": round(max(0.0, float(observation.analyst_review_time_ms)), 6),
            "execution_latency_ms": round(max(0.0, float(observation.execution_latency_ms)), 6),
            "repeated_investigation_reuse": int(observation.repeated_investigation_reuse),
            "knowledge_reuse_rate": round(float(observation.knowledge_reuse_rate), 6),
        }

    @staticmethod
    def improvement(baseline: dict[str, float | int], enhanced: dict[str, float | int]) -> dict[str, float | int]:
        baseline_fp = int(baseline["false_positive_count"])
        enhanced_fp = int(enhanced["false_positive_count"])
        baseline_fn = int(baseline["false_negative_count"])
        enhanced_fn = int(enhanced["false_negative_count"])
        return {
            "verdict_agreement_change": round(float(enhanced["verdict_agreement"]) - float(baseline["verdict_agreement"]), 6),
            "false_positive_reduction": round((baseline_fp - enhanced_fp) / max(1, baseline_fp), 6),
            "false_negative_detection": max(0, baseline_fn - enhanced_fn),
            "evidence_relevance_improvement": round(float(enhanced["evidence_relevance"]) - float(baseline["evidence_relevance"]), 6),
            "mitre_mapping_accuracy_change": round(float(enhanced["mitre_mapping_accuracy"]) - float(baseline["mitre_mapping_accuracy"]), 6),
            "ioc_relationship_accuracy_change": round(float(enhanced["ioc_relationship_accuracy"]) - float(baseline["ioc_relationship_accuracy"]), 6),
            "confidence_calibration_change": round(float(enhanced["confidence_calibration"]) - float(baseline["confidence_calibration"]), 6),
            "uncertainty_reduction": round(float(baseline["uncertainty_score"]) - float(enhanced["uncertainty_score"]), 6),
            "reasoning_completeness_change": round(float(enhanced["reasoning_completeness"]) - float(baseline["reasoning_completeness"]), 6),
            "provenance_coverage_improvement": round(float(enhanced["provenance_coverage"]) - float(baseline["provenance_coverage"]), 6),
            "evidence_citation_coverage_improvement": round(float(enhanced["evidence_citation_coverage"]) - float(baseline["evidence_citation_coverage"]), 6),
            "analyst_review_time_reduction_ms": round(float(baseline["analyst_review_time_ms"]) - float(enhanced["analyst_review_time_ms"]), 6),
            "execution_latency_change_ms": round(float(enhanced["execution_latency_ms"]) - float(baseline["execution_latency_ms"]), 6),
            "repeated_investigation_reuse_change": int(enhanced["repeated_investigation_reuse"]) - int(baseline["repeated_investigation_reuse"]),
            "knowledge_reuse_rate_change": round(float(enhanced["knowledge_reuse_rate"]) - float(baseline["knowledge_reuse_rate"]), 6),
        }

    @staticmethod
    def memory_benefit_score(improvement: dict[str, float | int]) -> float:
        keys = (
            "verdict_agreement_change", "evidence_relevance_improvement",
            "mitre_mapping_accuracy_change", "ioc_relationship_accuracy_change",
            "confidence_calibration_change", "uncertainty_reduction",
            "reasoning_completeness_change", "provenance_coverage_improvement",
            "evidence_citation_coverage_improvement", "knowledge_reuse_rate_change",
        )
        return round(sum(max(0.0, float(improvement.get(key, 0.0))) for key in keys) / len(keys), 6)


__all__ = ["AccuracyMetrics"]
