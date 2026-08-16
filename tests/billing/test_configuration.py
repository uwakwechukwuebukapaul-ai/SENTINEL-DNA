import pytest
from services.billing.config import BillingConfiguration
from services.billing.exceptions import BillingConfigurationError
def test_disabled_by_default(): assert BillingConfiguration.from_environment({}).validate() is False
def test_enabled_requires_secure_configuration():
    with pytest.raises(BillingConfigurationError): BillingConfiguration(True,"http://paystack.test","","SECRET","WEBHOOK","https://app.test/callback").validate()
def test_enabled_configuration_is_valid_without_network():
    assert BillingConfiguration(True,"https://api.paystack.test","pk_test","SECRET","WEBHOOK","https://app.test/callback").validate() is True
