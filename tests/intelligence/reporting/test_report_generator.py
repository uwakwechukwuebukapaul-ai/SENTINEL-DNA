from services.intelligence.reporting.report_generator import (
    ReportGenerator,
)



def test_report_generation():

    generator = ReportGenerator()


    report = generator.generate(
        {
            "case_id": "CASE-100",
            "status": "completed",
            "results": [],
        }
    )


    assert (
        report["case_id"]
        ==
        "CASE-100"
    )


    assert (
        "summary"
        in report
    )


    assert (
        "timeline"
        in report
    )