from services.billing.config import BillingConfiguration
from services.billing.paystack import PaystackProviderValidator, ProviderValidationResult
from services.billing.readiness import evaluate_paystack_operations
from tests.credential_helpers import random_secret


class Response:
    status_code = 200
    content = b'{"status":true,"data":{}}'
    def json(self): return {"status": True, "data": {}}


class Transport:
    def get(self, *args, **kwargs): return Response()


class Provider:
    base_url = "https://api.paystack.co"
    secret = random_secret()
    timeout_seconds = 5
    transport = Transport()


def config():
    return BillingConfiguration(True, "https://api.paystack.co", "pk", "REF", "WEB", "https://app.test/callback")


def test_validation_is_explicit_and_injected():
    result = PaystackProviderValidator(Provider()).validate()
    assert result == ProviderValidationResult("PROVIDER_VALIDATED", "provider_authenticated")


def test_provider_validation_does_not_approve_production():
    validation = ProviderValidationResult("PROVIDER_VALIDATED", "provider_authenticated")
    result = evaluate_paystack_operations(configuration=config(), secret_available=True, provider_validation=validation, webhook_trust=True, authorization=True)
    assert result.state == "PROVIDER_VALIDATED"
    assert result.ready is True and result.production_approved is False
    assert result.as_dict()["checks"]["production_approval"] == "BLOCKED"


def test_disabled_configuration_is_deterministically_blocked():
    result = evaluate_paystack_operations(configuration=BillingConfiguration(), secret_available=False)
    assert result.state == "DISABLED" and not result.ready
