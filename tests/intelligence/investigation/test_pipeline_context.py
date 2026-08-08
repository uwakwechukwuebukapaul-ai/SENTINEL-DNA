from services.intelligence.investigation.pipeline_context import (
    InvestigationPipelineContext,
)



def test_context_creation():

    context = InvestigationPipelineContext(
        "CASE-1",
        {
            "source": "email"
        },
    )


    assert (
        context.status
        ==
        "initialized"
    )



def test_context_completion():

    context = InvestigationPipelineContext(
        "CASE-2",
        {},
    )


    context.complete()


    assert (
        context.status
        ==
        "completed"
    )