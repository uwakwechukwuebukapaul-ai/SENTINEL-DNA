import pytest

from services.intelligence.reasoning.evidence_sufficiency import EvidenceSufficiencyEvaluator, SufficiencyStatus
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_runtime_policy import (
    InvestigationPolicyViolation,
    InvestigationRuntimePolicy,
)


def job(**changes):
    values = {
        "job_id": "JOB-1", "tenant_id": "tenant-a", "case_id": "CASE-1", "investigation_id": "INV-1",
        "execution_id": "EXE-1", "trigger_id": "TRIGGER-1", "idempotency_key": "K-1",
        "actor_id": "actor-a", "service_identity": None, "correlation_id": "CORR-1",
    }
    values.update(changes)
    return InvestigationJob(**values)


def insufficient():
    return EvidenceSufficiencyEvaluator().evaluate(
        {
            "success": True, "status": "completed", "evidence": [{"evidence_id": "E-1"}],
            "evidence_sufficiency": "INSUFFICIENT", "evidence_gaps": ["host timeline"],
            "recommended_follow_up": {
                "capability": "evidence_lookup", "required_evidence": ["host timeline"],
                "authorization_reference": "policy:read-only-evidence",
            },
        }, case_id="CASE-1", investigation_id="INV-1", tenant_id="tenant-a", correlation_id="CORR-1"
    )


def test_policy_requires_exactly_one_iteration_and_builds_deterministic_lineage():
    policy = InvestigationRuntimePolicy()
    first = policy.create_follow_up_task(job=job(), parent_task_id="INITIAL-JOB-1", sufficiency=insufficient(), now="2026-08-24T00:00:00+00:00")
    second = policy.create_follow_up_task(job=job(), parent_task_id="INITIAL-JOB-1", sufficiency=insufficient(), now="2026-08-24T00:00:00+00:00")
    assert first.to_dict() == second.to_dict()
    assert first.iteration == 1
    assert first.parent_task_id == "INITIAL-JOB-1"
    assert first.required_evidence == ["host timeline"]


def test_policy_rejects_second_iteration_and_destructive_or_unauthorized_capability():
    policy = InvestigationRuntimePolicy()
    with pytest.raises(InvestigationPolicyViolation):
        policy.create_follow_up_task(job=job(iteration=1), parent_task_id="P", sufficiency=insufficient())
    destructive = insufficient()
    object.__setattr__(destructive, "recommended_follow_up", {
        "capability": "isolate_host", "authorization_reference": "policy:bad", "required_evidence": ["host timeline"]
    })
    with pytest.raises(InvestigationPolicyViolation):
        policy.create_follow_up_task(job=job(), parent_task_id="P", sufficiency=destructive)


def test_policy_fails_closed_on_cancellation_and_missing_authorization():
    policy = InvestigationRuntimePolicy()
    with pytest.raises(InvestigationPolicyViolation):
        policy.create_follow_up_task(job=job(), parent_task_id="P", sufficiency=insufficient(), cancellation_requested=True)
    missing = insufficient()
    object.__setattr__(missing, "recommended_follow_up", {"capability": "evidence_lookup", "required_evidence": ["host timeline"]})
    with pytest.raises(InvestigationPolicyViolation):
        policy.create_follow_up_task(job=job(), parent_task_id="P", sufficiency=missing)


def test_policy_hooks_and_budget_are_enforced():
    policy = InvestigationRuntimePolicy(tenant_quota_hook=lambda *_: False)
    with pytest.raises(InvestigationPolicyViolation):
        policy.create_follow_up_task(job=job(), parent_task_id="P", sufficiency=insufficient())
    with pytest.raises(InvestigationPolicyViolation):
        InvestigationRuntimePolicy(max_iterations=2)
