from services.intelligence.reporting.report_repository import (
    ReportRepository,
)
from database.connection import DatabaseConnection
from services.intelligence.repository.report_repository import InvestigationReportRepository


def test_save_report():

    repo = ReportRepository()

    report = {
        "severity": "critical",
        "summary": "phishing investigation",
    }

    result = repo.save(
        "CASE-001",
        report,
    )

    assert result == report



def test_get_report():

    repo = ReportRepository()

    repo.save(
        "CASE-001",
        {
            "status": "complete"
        },
    )

    result = repo.get(
        "CASE-001"
    )

    assert result["status"] == "complete"



def test_report_exists():

    repo = ReportRepository()

    repo.save(
        "CASE-001",
        {},
    )

    assert repo.exists(
        "CASE-001"
    )



def test_delete_report():

    repo = ReportRepository()

    repo.save(
        "CASE-001",
        {},
    )

    assert repo.delete(
        "CASE-001"
    )

    assert not repo.exists(
        "CASE-001"
    )



def test_clear_reports():

    repo = ReportRepository()

    repo.save(
        "CASE-001",
        {},
    )

    repo.clear()

    assert repo.list_all() == []


def test_canonical_report_repository_survives_repository_recreation(tmp_path):
    db = DatabaseConnection(tmp_path / "reports.db")
    first = InvestigationReportRepository(db)
    first.save({"case_id": "CASE-RESTART", "summary": "durable", "tenant_context": {"tenant_id": "tenant-a"}})

    recreated = InvestigationReportRepository(DatabaseConnection(tmp_path / "reports.db"))
    assert recreated.get_by_case_id("CASE-RESTART") == {
        "case_id": "CASE-RESTART",
        "summary": "durable",
        "tenant_context": {"tenant_id": "tenant-a"},
    }


def test_canonical_report_repository_upserts_latest_report(tmp_path):
    repo = InvestigationReportRepository(DatabaseConnection(tmp_path / "reports.db"))
    repo.save({"case_id": "CASE-LATEST", "summary": "old"})
    repo.save({"case_id": "CASE-LATEST", "summary": "new"})

    assert repo.get_by_case_id("CASE-LATEST")["summary"] == "new"
    assert len(repo.get_all()) == 1
