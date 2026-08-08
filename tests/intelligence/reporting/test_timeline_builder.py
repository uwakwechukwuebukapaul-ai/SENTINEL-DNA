from services.intelligence.reporting.timeline_builder import (
    TimelineBuilder,
)



def test_timeline_creation():

    builder = TimelineBuilder()


    result = builder.build(
        {
            "case_id": "CASE-1"
        }
    )


    assert len(result) == 1