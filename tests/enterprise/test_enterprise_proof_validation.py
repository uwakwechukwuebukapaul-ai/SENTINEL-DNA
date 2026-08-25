import pytest

from services.intelligence.enterprise_proof import (
    AnalystEffectivenessBenchmarker,
    EnterpriseProofReportGenerator,
    EnterpriseProofValidator,
    InvestigationScaleBenchmarker,
    TenantIsolationCertifier,
)


def test_tenant_certification_denies_cross_tenant_memory_reads_and_preserves_provenance():
    certification = TenantIsolationCertifier().run()

    assert certification.certification_result == "passed"
    assert certification.tenant_ids == ("tenant-proof-a", "tenant-proof-b")
    assert certification.memory_isolation_valid is True
    assert certification.organizational_memory_isolation_valid is True
    assert certification.evidence_provenance_valid is True
    assert certification.cross_tenant_access_denied is True
    cross_tenant = [
        item for item in certification.access_attempts
        if item.requester_tenant_id != item.owner_tenant_id
    ]
    assert cross_tenant
    assert all(not item.allowed for item in cross_tenant)
    assert all(item.observed_tenant_id is None and not item.observed_provenance for item in cross_tenant)


def test_tenant_certification_replay_is_deterministic():
    first = TenantIsolationCertifier().run()
    second = TenantIsolationCertifier().run()
    assert first.replay_digest == second.replay_digest


def test_analyst_effectiveness_benchmark_measures_operational_gain():
    benchmark = AnalystEffectivenessBenchmarker().run()

    assert len(benchmark.cases) == 8
    assert benchmark.investigation_time_reduction_ms > 0
    assert benchmark.investigation_time_reduction_rate > 0
    assert benchmark.analyst_confidence_improvement > 0
    assert benchmark.ai_confidence_improvement > 0
    assert benchmark.recommendation_acceptance_rate == 1.0
    assert benchmark.false_escalations_baseline == 1
    assert benchmark.false_escalations_enhanced == 0
    assert benchmark.false_escalation_reduction == 1
    assert benchmark.evidence_provenance_preserved is True


def test_scale_benchmark_covers_required_sizes_and_percentiles():
    benchmark = InvestigationScaleBenchmarker().run()

    assert [point.investigation_count for point in benchmark.points] == [10, 100, 1000]
    for point in benchmark.points:
        assert point.baseline_p50_latency_ms <= point.baseline_p95_latency_ms
        assert point.enhanced_p50_latency_ms <= point.enhanced_p95_latency_ms
        assert point.enhanced_p95_latency_ms > point.baseline_p95_latency_ms
        assert point.memory_overhead_kb > 0
        assert point.memory_overhead_rate > 0


def test_scale_benchmark_replay_is_deterministic():
    assert InvestigationScaleBenchmarker().run().to_dict() == InvestigationScaleBenchmarker().run().to_dict()


def test_enterprise_report_preserves_safety_boundaries_and_contracts():
    first = EnterpriseProofValidator(generated_at="2026-08-25T00:00:00+00:00").run()
    second = EnterpriseProofValidator(generated_at="2026-08-25T00:00:00+00:00").run()

    assert first.immutable is True
    assert first.replay_digest == second.replay_digest
    assert first.report_digest == second.report_digest
    assert all(first.safety_validation.values())
    assert first.safety_validation["authorization_unchanged"] is True
    assert first.safety_validation["verdict_enforcement_unchanged"] is True
    assert first.safety_validation["tenant_isolation_unchanged"] is True
    assert first.safety_validation["fail_closed_behavior_unchanged"] is True
    assert first.safety_validation["investigation_result_contract_unchanged"] is True
    assert first.safety_validation["memory_advisory_only"] is True
    assert first.safety_validation["response_automation_unchanged"] is True
    assert first.safety_validation["cross_tenant_access_denied"] is True
    assert first.safety_validation["append_only_evidence"] is True
    assert first.safety_validation["deterministic_replay_valid"] is True


def test_enterprise_report_write_is_append_only(tmp_path):
    report = EnterpriseProofReportGenerator(
        EnterpriseProofValidator(generated_at="2026-08-25T00:00:00+00:00")
    ).generate()
    target = tmp_path / "enterprise-proof.json"
    generator = EnterpriseProofReportGenerator()

    assert generator.write(report, target) == target
    with pytest.raises(FileExistsError, match="immutable_enterprise_proof_exists"):
        generator.write(report, target)
