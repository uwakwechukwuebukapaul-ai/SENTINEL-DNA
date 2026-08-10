"""
Investigation View Tests.

Validates analyst-facing investigation representation.
"""

import sys
from pathlib import Path


# Make the repository root importable when this test is run directly.
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.intelligence.workspace.investigation_view import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    InvestigationView,
)



def create_view():

    return InvestigationView()



def sample_data():

    return {
        "case_id": "CASE-001",
        "risk": "high",
        "confidence": 0.88,
        "findings": [
            "Suspicious login",
        ],
        "indicators": [
            "evil.com",
        ],
        "mitre": [
            "T1566",
        ],
        "recommendations": [
            "Reset credentials",
        ],
    }



def test_view_creation():

    view = create_view()

    assert view is not None



def test_render_view():

    view = create_view()

    result = view.render(
        sample_data()
    )

    assert result is not None



def test_view_case_id():

    view = create_view()

    result = view.render(
        sample_data()
    )

    assert (
        result["case_id"]
        ==
        "CASE-001"
    )



def test_view_risk():

    view = create_view()

    result = view.render(
        sample_data()
    )

    assert (
        result["risk"]
        ==
        "high"
    )



def test_view_empty():

    view = create_view()

    result = view.render({})

    assert result is not None