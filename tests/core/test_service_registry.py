"""
Sentinel DNA Service Registry Tests.

Validates dependency container behavior.
"""

from services.core.service_registry import (
    ServiceRegistry,
)


class FakeService:
    """
    Test service object.
    """

    pass



def test_register_service():
    """
    Registered service can be retrieved.
    """

    registry = ServiceRegistry()

    service = FakeService()


    registry.register(
        "fake_service",
        service,
    )


    result = registry.get(
        "fake_service"
    )


    assert result is service



def test_missing_service_returns_none():
    """
    Missing services return None.
    """

    registry = ServiceRegistry()


    assert registry.get(
        "missing"
    ) is None



def test_has_service():
    """
    Registry detects existing services.
    """

    registry = ServiceRegistry()

    registry.register(
        "service",
        FakeService(),
    )


    assert registry.has(
        "service"
    ) is True


    assert registry.has(
        "missing"
    ) is False



def test_all_services_returns_copy():
    """
    Registry exposes registered services.
    """

    registry = ServiceRegistry()

    service = FakeService()


    registry.register(
        "service",
        service,
    )


    services = registry.all()


    assert "service" in services

    assert services["service"] is service



def test_clear_registry():
    """
    Registry can clear dependencies.
    """

    registry = ServiceRegistry()


    registry.register(
        "service",
        FakeService(),
    )


    registry.clear()


    assert registry.all() == {}

    assert registry.has(
        "service"
    ) is False