from decimal import Decimal
import pytest
from services.billing.config import CryptoConfiguration, EnvironmentSecretProvider
from services.billing.crypto import CryptoPaymentProvider, CryptoPaymentRequest
from services.billing.exceptions import BillingConfigurationError, PaymentProviderError
from tests.credential_helpers import random_secret

CRYPTO_SECRET = random_secret()

class Response:
    status_code = 200; content = b'{"data":{}}'
    def __init__(self, data): self._data = data; self.content = b'x'
    def json(self): return {"data": self._data}
class Transport:
    def post(self, *args, **kwargs): return Response({"provider_reference":"p-1","payment_address":"treasury","expires_at":"2030-01-01T00:00:00Z"})
class Secret:
    def get(self, ref): return CRYPTO_SECRET if ref == "CRYPTO_KEY" else ""

def provider(): return CryptoPaymentProvider(provider="processor", base_url="https://crypto.example.test", secret_provider=Secret(), secret_reference="CRYPTO_KEY", assets=("USDC",), networks=("Ethereum",), transport=Transport())
def test_crypto_disabled_and_valid_configuration():
    assert CryptoConfiguration().reason_codes() == ("CRYPTO_DISABLED",)
    assert CryptoConfiguration(True,"processor",("USDC",),("Ethereum",),"https://crypto.example.test","KEY","WEB").reason_codes() == ("CRYPTO_READY",)
def test_crypto_configuration_and_secret_fail_closed():
    with pytest.raises(BillingConfigurationError): CryptoPaymentProvider(provider="p", base_url="http://localhost", secret_provider=Secret(), secret_reference="CRYPTO_KEY", assets=("USDC",), networks=("Ethereum",))
    with pytest.raises(BillingConfigurationError): CryptoPaymentProvider(provider="p", base_url="https://crypto.example.test", secret_provider=Secret(), secret_reference="MISSING", assets=("USDC",), networks=("Ethereum",))
def test_payment_creation_is_decimal_and_server_referenced():
    payment = provider().create_payment(CryptoPaymentRequest("PRO","USDC","Ethereum",Decimal("12.340000"),6,1800))
    assert payment.reference.startswith("sdna_crypto_") and payment.amount == Decimal("12.340000")
    assert provider().verify_payment(payment=payment, provider_reference="p-1", amount="12.340000", asset="USDC", network="Ethereum", recipient="treasury")
    with pytest.raises(PaymentProviderError): provider().verify_payment(payment=payment, provider_reference="p-1", amount="12.34", asset="USDT", network="Ethereum", recipient="treasury")
def test_provider_event_normalization_rejects_untrusted_shape():
    with pytest.raises(PaymentProviderError): provider().normalize_event({"status":"confirmed"})
    assert provider().normalize_event({"event_id":"e-1","status":"confirmed"})["event_type"] == "CRYPTO_PAYMENT_CONFIRMED"

def test_confirmation_and_expiration_are_verified_server_side():
    payment = provider().create_payment(CryptoPaymentRequest("PRO", "USDC", "Ethereum", Decimal("1"), 6, 1800))
    with pytest.raises(PaymentProviderError): provider().verify_payment(payment=payment, provider_reference="p-1", amount="1", asset="USDC", network="Ethereum", recipient="treasury", confirmations=0, required_confirmations=2)
    with pytest.raises(PaymentProviderError): provider().verify_payment(payment=payment, provider_reference="p-1", amount="1", asset="USDC", network="Ethereum", recipient="treasury", confirmations=2, expired=True)
