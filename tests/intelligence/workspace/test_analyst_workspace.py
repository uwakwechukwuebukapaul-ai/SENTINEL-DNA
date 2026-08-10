"""
Analyst Workspace Tests.

Validates:

- workspace creation
- investigation loading
- summary generation
- empty investigations
- failed investigations
"""

from services.intelligence.workspace.analyst_workspace import (  # pyright: ignore[reportMissingImports]
    AnalystWorkspace,
)


def create_workspace():

    return AnalystWorkspace()



def sample_investigation():

    return {
        "investigation_id": "INV-001",
        "case_id": "CASE-001",
        "status": "completed",
        "risk": "critical",
        "confidence": 0.95,
        "findings": [
            "Credential phishing detected",
        ],
        "indicators": [
            "evil.com",
        ],
        "recommendations": [
            "Block domain",
        ],
    }



def test_workspace_creation():

    workspace = create_workspace()

    assert workspace is not None



def test_load_investigation():

    workspace = create_workspace()

    result = workspace.load(
        sample_investigation()
    )

    assert result is not None



def test_workspace_contains_case():

    workspace = create_workspace()

    result = workspace.load(
        sample_investigation()
    )

    assert (
        result["case_id"]
        ==
        "CASE-001"
    )



def test_workspace_empty_investigation():

    workspace = create_workspace()

    result = workspace.load({})

    assert result is not None



def test_workspace_failed_investigation():

    workspace = create_workspace()

    result = workspace.load(
        {
            "status": "failed",
            "error": "engine failure",
        }
    )

    assert result["status"] == "failed"