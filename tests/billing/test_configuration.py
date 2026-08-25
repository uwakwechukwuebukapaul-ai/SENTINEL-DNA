import pytest
from services.billing.config import BillingConfiguration, EnvironmentSecretProvider
from tests.credential_helpers import random_secret

PROVIDER_SECRET = random_secret()
from services.billing.exceptions import BillingConfigurationError
def test_disabled_by_default(): assert BillingConfiguration.from_environment({}).validate() is False
def test_enabled_requires_secure_configuration():
    with pytest.raises(BillingConfigurationError): BillingConfiguration(True,"http://paystack.test","","SECRET","WEBHOOK","https://app.test/callback").validate()
def test_enabled_configuration_is_valid_without_network():
    assert BillingConfiguration(True,"https://api.paystack.test","pk_test","SECRET","WEBHOOK","https://app.test/callback").validate() is True

def test_configuration_exposes_only_non_secret_reason_codes():
    config = BillingConfiguration.from_environment({})
    assert config.reason_codes() == ("PAYSTACK_DISABLED",)
    assert "PAYSTACK" in " ".join(config.reason_codes())
    assert "SECRET" not in " ".join(config.reason_codes())

def test_unsafe_endpoint_and_callback_are_blocked():
    with pytest.raises(BillingConfigurationError):
        BillingConfiguration(True,"http://api.paystack.co","pk","SECRET","WEBHOOK","https://app.test/callback").validate()
    with pytest.raises(BillingConfigurationError):
        BillingConfiguration(True,"https://api.paystack.co","pk","SECRET","WEBHOOK","https://app.test/callback#secret").validate()

def test_secret_provider_resolves_reference_without_diagnostic_exposure():
    provider = EnvironmentSecretProvider({"PAYSTACK_SECRET_REF": PROVIDER_SECRET})
    assert provider.get("PAYSTACK_SECRET_REF") == PROVIDER_SECRET
    assert provider.get("MISSING") == ""
