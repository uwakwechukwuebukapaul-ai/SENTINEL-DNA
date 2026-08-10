"""
Sentinel DNA API Dependency Injection Tests.
"""

from importlib import import_module


create_app = import_module("app").create_app



def test_investigation_service_from_container():

    app = create_app()


    service = app.container.get(
        "investigation_orchestrator"
    )


    assert service is not None



def test_dashboard_service_from_container():

    app = create_app()


    service = app.container.get(
        "dashboard_service"
    )


    assert service is not None