from services.intelligence.investigation.pipeline import (
    InvestigationPipeline,
)



def test_pipeline_execution():

    pipeline = InvestigationPipeline()


    result = pipeline.run(
        "CASE-100",
        {
            "source": "email",
            "severity": "high",
        },
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        len(result["results"])
        ==
        5
    )