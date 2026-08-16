import pytest

from services.domain_contracts import Outcome, OutcomePersistenceBoundary, OutcomeStatus
from services.intelligence.outcome_learning.repository import OutcomeLearningRepository


def test_outcome_boundary_round_trips_through_authoritative_repository():
    repository = OutcomeLearningRepository()
    boundary = OutcomePersistenceBoundary(repository)
    original = Outcome("tenant-a", "life-1", "out-1", status=OutcomeStatus.SUCCESS, verification_status=OutcomeStatus.SUCCESS, evidence_references=("e1",))

    assert boundary.save(original) == original
    restored = boundary.list("tenant-a")
    assert len(restored) == 1
    assert restored[0].to_dict() == original.to_dict()


def test_outcome_boundary_preserves_repository_deduplication():
    repository = OutcomeLearningRepository()
    boundary = OutcomePersistenceBoundary(repository)
    outcome = Outcome("tenant-a", "life-1", "out-1")

    boundary.save(outcome)
    boundary.save(outcome)
    assert len(repository.list_outcomes("tenant-a")) == 1


def test_outcome_boundary_is_tenant_aware_and_rejects_invalid_inputs():
    boundary = OutcomePersistenceBoundary(OutcomeLearningRepository())
    with pytest.raises(ValueError, match="tenant_id_required"):
        boundary.list("  ")
    with pytest.raises(TypeError, match="outcome_required"):
        boundary.save({})
