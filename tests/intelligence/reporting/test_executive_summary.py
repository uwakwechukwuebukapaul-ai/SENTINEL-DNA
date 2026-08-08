from services.intelligence.reporting.executive_summary import (
    ExecutiveSummaryGenerator,
)



def test_summary_generation():

    generator = ExecutiveSummaryGenerator()


    result = generator.generate(
        {
            "case_id": "CASE-1",
            "status": "completed",
            "results": [
                {}
            ],
        }
    )


    assert "CASE-1" in result