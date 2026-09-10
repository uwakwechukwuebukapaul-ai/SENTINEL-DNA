"""
Integration tests for investigation persistence.
"""

from __future__ import annotations

from services.investigation_runtime.persistence import (
    InvestigationRepository,
    SQLiteInvestigationRepository,
)

from services.investigation_runtime.state import (
    InvestigationState,
    InvestigationStatus,
)


def test_sqlite_repository_implements_contract(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    assert isinstance(
        repository,
        InvestigationRepository,
    )


def test_create_and_get_investigation(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    state = InvestigationState(
        investigation_id="INV-100",
        investigation={
            "source": "endpoint",
            "indicator": "powershell",
        },
    )

    repository.create(state)

    loaded = repository.get(
        "INV-100"
    )

    assert loaded.investigation_id == "INV-100"
    assert loaded.status == InvestigationStatus.PENDING
    assert loaded.investigation["indicator"] == (
        "powershell"
    )


def test_repository_round_trips_stage_results_and_metadata(tmp_path):
    repository = SQLiteInvestigationRepository(tmp_path / "investigations.db")
    state = InvestigationState(
        investigation_id="INV-STATE",
        investigation={"source": "endpoint"},
        current_stage="correlation",
        completed_stages=["intake"],
        results={"intake": {"accepted": True}},
        metadata={"tenant_id": "tenant-a", "provenance": "synthetic"},
    )

    repository.create(state)
    loaded = repository.get("INV-STATE")

    assert loaded.current_stage == "correlation"
    assert loaded.completed_stages == ["intake"]
    assert loaded.results == {"intake": {"accepted": True}}
    assert loaded.metadata == {"tenant_id": "tenant-a", "provenance": "synthetic"}


def test_repository_exists(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    assert not repository.exists(
        "INV-101"
    )

    repository.create(
        InvestigationState(
            investigation_id="INV-101",
            investigation={},
        )
    )

    assert repository.exists(
        "INV-101"
    )


def test_update_persists_lifecycle(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    state = InvestigationState(
        investigation_id="INV-102",
        investigation={
            "indicator": "malicious.exe",
        },
    )

    repository.create(state)

    state.start()

    state.complete(
        intelligence={
            "risk": {
                "score": 95,
                "severity": "critical",
            }
        },
        confidence={
            "score": 0.95,
            "level": "high",
        },
        finding={
            "risk": "critical",
        },
    )

    repository.update(state)

    loaded = repository.get(
        "INV-102"
    )

    assert loaded.status == (
        InvestigationStatus.COMPLETED
    )

    assert loaded.intelligence["risk"]["score"] == 95

    assert loaded.confidence["score"] == 0.95

    assert loaded.finding["risk"] == "critical"

    assert loaded.started_at is not None
    assert loaded.completed_at is not None


def test_failure_is_persisted(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    state = InvestigationState(
        investigation_id="INV-103",
        investigation={},
    )

    repository.create(state)

    state.start()

    state.fail(
        "MITRE provider unavailable",
        service="mitre_intelligence",
    )

    repository.update(state)

    loaded = repository.get(
        "INV-103"
    )

    assert loaded.status == (
        InvestigationStatus.FAILED
    )

    assert len(loaded.errors) == 1

    assert loaded.errors[0]["error"] == (
        "MITRE provider unavailable"
    )

    assert loaded.errors[0]["service"] == (
        "mitre_intelligence"
    )


def test_list_investigations(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    repository.create(
        InvestigationState(
            investigation_id="INV-104",
            investigation={},
        )
    )

    repository.create(
        InvestigationState(
            investigation_id="INV-105",
            investigation={},
        )
    )

    investigations = repository.list()

    assert len(investigations) == 2

    assert [
        state.investigation_id
        for state in investigations
    ] == [
        "INV-104",
        "INV-105",
    ]


def test_delete_investigation(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    repository.create(
        InvestigationState(
            investigation_id="INV-106",
            investigation={},
        )
    )

    deleted = repository.delete(
        "INV-106"
    )

    assert deleted.investigation_id == "INV-106"
    assert not repository.exists(
        "INV-106"
    )


def test_duplicate_investigation_is_rejected(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    state = InvestigationState(
        investigation_id="INV-107",
        investigation={},
    )

    repository.create(state)

    try:
        repository.create(state)
        assert False, (
            "Expected duplicate investigation "
            "to be rejected."
        )
    except ValueError:
        pass


def test_missing_investigation_is_rejected(
    tmp_path,
):
    repository = SQLiteInvestigationRepository(
        tmp_path / "investigations.db"
    )

    try:
        repository.get(
            "DOES-NOT-EXIST"
        )
        assert False, (
            "Expected missing investigation "
            "to raise KeyError."
        )
    except KeyError:
        pass
