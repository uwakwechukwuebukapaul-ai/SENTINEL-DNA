"""
Sentinel DNA Flask Container Tests.
"""

import sys
from pathlib import Path


# Ensure the project root is importable when this test is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app  # pyright: ignore[reportMissingImports]



def test_app_has_container():

    app = create_app()


    assert hasattr(
        app,
        "container",
    )



def test_container_has_core_services():

    app = create_app()


    container = app.container


    assert container.get(
        "case_manager"
    ) is not None


    assert container.get(
        "investigation_orchestrator"
    ) is not None


    assert container.get(
        "dashboard_service"
    ) is not None