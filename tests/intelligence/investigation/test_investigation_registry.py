"""
Sentinel DNA Investigation Registry Tests
"""

from __future__ import annotations


from services.intelligence.investigation.investigation_registry import (
    InvestigationRegistry,
)



class FakeEngine:
    pass



def test_register_component():

    registry = InvestigationRegistry()


    engine = FakeEngine()


    registry.register(
        "threat_engine",
        engine,
    )


    assert (
        registry.exists(
            "threat_engine"
        )
    )



def test_get_component():

    registry = InvestigationRegistry()


    engine = FakeEngine()


    registry.register(
        "risk_engine",
        engine,
    )


    result = registry.get(
        "risk_engine"
    )


    assert result is engine



def test_list_components():

    registry = InvestigationRegistry()


    registry.register(
        "mitre_engine",
        FakeEngine(),
    )


    registry.register(
        "intel_engine",
        FakeEngine(),
    )


    components = (
        registry.list_components()
    )


    assert len(components) == 2



def test_unregister_component():

    registry = InvestigationRegistry()


    registry.register(
        "test_engine",
        FakeEngine(),
    )


    registry.unregister(
        "test_engine"
    )


    assert (
        registry.exists(
            "test_engine"
        )
        is False
    )



def test_clear_registry():

    registry = InvestigationRegistry()


    registry.register(
        "engine",
        FakeEngine(),
    )


    registry.clear()


    assert (
        registry.list_components()
        ==
        []
    )