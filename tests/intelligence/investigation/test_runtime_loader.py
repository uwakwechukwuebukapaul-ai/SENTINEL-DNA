"""
Sentinel DNA Investigation Runtime Loader Tests
"""

from __future__ import annotations


from services.intelligence.investigation.runtime_loader import (
    InvestigationRuntimeLoader,
)



class FakeEngine:
    pass



def test_load_component():

    loader = InvestigationRuntimeLoader()


    loader.load_component(
        "mitre_engine",
        FakeEngine(),
    )


    assert (
        loader.registry.exists(
            "mitre_engine"
        )
    )



def test_bulk_component_loading():

    loader = InvestigationRuntimeLoader()


    loader.load_components(
        {
            "risk_engine": FakeEngine(),
            "intel_engine": FakeEngine(),
        }
    )


    assert len(
        loader.registry.list_components()
    ) == 2



def test_runtime_start():

    loader = InvestigationRuntimeLoader()


    result = loader.start()


    assert (
        result["status"]
        ==
        "running"
    )


    assert (
        loader.loaded
        is True
    )



def test_runtime_status():

    loader = InvestigationRuntimeLoader()


    loader.load_component(
        "test_engine",
        FakeEngine(),
    )


    loader.start()


    status = loader.status()


    assert (
        status["loaded"]
        is True
    )


    assert (
        "test_engine"
        in status["components"]
    )



def test_runtime_stop():

    loader = InvestigationRuntimeLoader()


    loader.start()

    loader.stop()


    assert (
        loader.loaded
        is False
    )