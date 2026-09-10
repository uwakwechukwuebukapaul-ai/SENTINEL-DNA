import pytest

from services.intelligence.evaluation import (
    AccuracyMetrics,
    OperationalAccuracyBenchmarkRunner,
    OperationalAccuracyEvaluator,
    default_synthetic_soc_scenarios,
)


def test_dataset_covers_required_synthetic_soc_scenarios():
    scenarios = default_synthetic_soc_scenarios()
    assert {item.scenario_type for item in scenarios} == {
        "phishing_compromise",
        "credential_theft",
        "malware_execution",
        "suspicious_authentication",
        "lateral_movement",
        "command_and_control",
        "benign_false_positive",
        "multi_ioc_investigation",
    }
    assert len({item.tenant_id for item in scenarios}) == 1


def test_metric_calculation_and_improvement_are_bounded_and_deterministic():
    scenario = default_synthetic_soc_scenarios()[0]
    evaluation = OperationalAccuracyEvaluator().evaluate_scenario(scenario)
    baseline = evaluation.metrics["baseline"]
    enhanced = evaluation.metrics["organizational_memory"]
    improvement = evaluation.metrics["organizational_memory_improvement"]

    assert baseline["verdict_agreement"] == 0.0
    assert enhanced["verdict_agreement"] == 1.0
    assert improvement["false_negative_detection"] == 1
    assert improvement["evidence_relevance_improvement"] >= 0
    assert 0 <= baseline["confidence_calibration"] <= 1
    assert 0 <= enhanced["ioc_relationship_accuracy"] <= 1


def test_evaluator_preserves_safety_invariants_and_records_disagreements():
    evaluation = OperationalAccuracyEvaluator().evaluate_scenario(default_synthetic_soc_scenarios()[0])

    assert all(evaluation.safety.values())
    assert evaluation.observations["baseline"].disagreement_reasons
    assert evaluation.observations["organizational_memory"].enforced_verdict == "review_required"
    assert evaluation.observations["baseline"].enforced_verdict == evaluation.observations["organizational_memory"].enforced_verdict


def test_benchmark_replay_is_stable_and_memory_improves_quality():
    first = OperationalAccuracyBenchmarkRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    second = OperationalAccuracyBenchmarkRunner(generated_at="2026-08-25T00:00:00+00:00").run()

    assert first.scenario_count == 8
    assert first.memory_benefit_score > 0
    assert first.aggregate_metrics["organizational_memory"]["verdict_agreement"] > first.aggregate_metrics["baseline"]["verdict_agreement"]
    assert first.latency_impact["organizational_memory_delta_ms"] > 0
    assert all(first.safety_validation.values())
    assert first.replay_digest == second.replay_digest
    assert first.report_digest == second.report_digest
    assert first.immutable is True


def test_benchmark_rejects_mixed_tenant_dataset():
    scenarios = list(default_synthetic_soc_scenarios())
    scenarios[-1] = type(scenarios[-1])(
        **{**scenarios[-1].to_dict(), "tenant_id": "tenant-other"}
    )
    with pytest.raises(PermissionError, match="evaluation_dataset_tenant_mismatch"):
        OperationalAccuracyBenchmarkRunner(scenarios).run()


def test_metric_false_positive_reduction():
    scenario = default_synthetic_soc_scenarios()[6]
    evaluation = OperationalAccuracyEvaluator().evaluate_scenario(scenario)
    assert evaluation.metrics["organizational_memory_improvement"]["false_positive_reduction"] == 1.0


def test_report_safety_names_are_explicit():
    report = OperationalAccuracyBenchmarkRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    assert report.safety_validation["authorization_unchanged"] is True
    assert report.safety_validation["verdict_enforcement_unchanged"] is True
    assert report.safety_validation["tenant_isolation_unchanged"] is True
    assert report.safety_validation["fail_closed_behavior_unchanged"] is True
    assert report.safety_validation["investigation_result_contract_unchanged"] is True


def test_validation_report_write_is_append_only(tmp_path):
    runner = OperationalAccuracyBenchmarkRunner(generated_at="2026-08-25T00:00:00+00:00")
    report = runner.run()
    target = tmp_path / "operational-accuracy-validation.json"

    assert runner.write(report, target) == target
    with pytest.raises(FileExistsError, match="immutable_validation_report_exists"):
        runner.write(report, target)
