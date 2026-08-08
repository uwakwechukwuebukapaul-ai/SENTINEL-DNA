"""
Sentinel DNA Investigation Runtime Manager Tests
"""

from __future__ import annotations


from services.intelligence.investigation.runtime_manager import (
    InvestigationRuntimeManager,
)



def test_runtime_initial_state():

    manager = InvestigationRuntimeManager()


    assert (
        manager.state
        ==
        "initialized"
    )



def test_runtime_start():

    manager = InvestigationRuntimeManager()


    result = manager.start()


    assert (
        result["status"]
        ==
        "running"
    )


    assert (
        manager.state
        ==
        "running"
    )



def test_runtime_stop():

    manager = InvestigationRuntimeManager()


    manager.start()

    result = manager.stop()


    assert (
        result["state"]
        ==
        "stopped"
    )



def test_runtime_restart():

    manager = InvestigationRuntimeManager()


    manager.start()


    result = manager.restart()


    assert (
        manager.state
        ==
        "running"
    )


    assert (
        result["status"]
        ==
        "running"
    )



def test_runtime_health():

    manager = InvestigationRuntimeManager()


    manager.start()


    health = manager.health()


    assert (
        health["healthy"]
        is True
    )