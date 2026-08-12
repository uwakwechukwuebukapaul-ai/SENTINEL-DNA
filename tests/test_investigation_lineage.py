from sentinel_dna.investigation.context import (
    InvestigationContext,
)


def test_context_has_lineage_components():

    context = InvestigationContext(
        case_id="INC-001",
        alert={
            "title": "Suspicious Login"
        },
    )


    assert context.graph is not None

    assert context.provenance is None

    assert context.replay is None