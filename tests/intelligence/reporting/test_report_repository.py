from services.intelligence.reporting.report_repository import (
    ReportRepository,
)


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