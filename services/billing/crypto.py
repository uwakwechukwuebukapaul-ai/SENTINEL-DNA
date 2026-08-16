"""Provider-neutral, non-custodial cryptocurrency payment adapter."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import uuid
from typing import Protocol
from .exceptions import BillingConfigurationError, PaymentProviderError

class CryptoSecretProvider(Protocol):
    def get(self, reference: str) -> str: ...

@dataclass(frozen=True)
class CryptoPaymentRequest:
    plan_id: str; asset: str; network: str; amount: Decimal; amount_decimals: int; expiration_seconds: int

@dataclass(frozen=True)
class CryptoPayment:
    provider: str; asset: str; network: str; amount: Decimal; reference: str; provider_reference: str; payment_address: str; expires_at: str; status: str

class CryptoPaymentProvider:
    def __init__(self, *, provider, base_url, secret_provider, secret_reference, assets, networks, timeout_seconds=10, transport=None):
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment: raise BillingConfigurationError("crypto_https_or_endpoint_invalid")
        if timeout_seconds <= 0 or timeout_seconds > 30 or not assets or not networks: raise BillingConfigurationError("crypto_configuration_invalid")
        self.provider, self.base_url, self.assets, self.networks = provider, base_url.rstrip("/"), frozenset(assets), frozenset(networks); self.timeout_seconds = timeout_seconds; self.transport = transport
        self.secret = secret_provider.get(secret_reference) if secret_reference else ""
        if not self.secret: raise BillingConfigurationError("crypto_secret_unavailable")
    def validate_configuration(self):
        return True
    def validate_provider(self):
        if self.transport is None: raise PaymentProviderError("crypto_transport_unavailable")
        return self._request("get", "/health") is not None
    def validate_sandbox(self):
        """Explicitly invoked, non-destructive capability validation."""
        data = self._request("get", "/capabilities")
        if not isinstance(data.get("provider"), str) or not isinstance(data.get("assets"), list) or not isinstance(data.get("networks"), list):
            raise PaymentProviderError("crypto_provider_response_invalid")
        return {"provider": data["provider"], "assets": tuple(data["assets"]), "networks": tuple(data["networks"])}
    def _request(self, method, path, payload=None):
        if self.transport is None: raise PaymentProviderError("crypto_transport_unavailable")
        response = getattr(self.transport, method)(self.base_url + path, headers={"Authorization": "Bearer " + self.secret, "Content-Type": "application/json"}, json=payload, timeout=self.timeout_seconds, allow_redirects=False)
        if getattr(response, "status_code", 0) != 200: raise PaymentProviderError("crypto_provider_request_failed")
        content = getattr(response, "content", b"")
        if content and len(content) > 256 * 1024: raise PaymentProviderError("crypto_provider_response_too_large")
        try: value = response.json()
        except Exception as exc: raise PaymentProviderError("crypto_provider_response_invalid") from exc
        if not isinstance(value, dict) or not isinstance(value.get("data"), dict): raise PaymentProviderError("crypto_provider_response_invalid")
        return value["data"]
    def create_payment(self, request: CryptoPaymentRequest):
        if request.asset not in self.assets or request.network not in self.networks or request.amount <= 0 or request.amount_decimals < 0: raise PaymentProviderError("crypto_payment_request_invalid")
        reference = "sdna_crypto_" + uuid.uuid4().hex
        data = self._request("post", "/payments", {"reference": reference, "asset": request.asset, "network": request.network, "amount": format(request.amount, "f"), "expiration_seconds": request.expiration_seconds})
        if not all(isinstance(data.get(key), str) and data[key] for key in ("provider_reference", "payment_address", "expires_at")): raise PaymentProviderError("crypto_provider_response_invalid")
        return CryptoPayment(self.provider, request.asset, request.network, request.amount, reference, data["provider_reference"], data["payment_address"], data["expires_at"], "PENDING")
    create_payment_intent = create_payment
    def get_payment_status(self, provider_reference):
        return self._request("get", "/payments/" + str(provider_reference))
    def verify_payment(self, *, payment: CryptoPayment, provider_reference, amount, asset, network, recipient, confirmations=0, required_confirmations=0, expired=False):
        if provider_reference != payment.provider_reference or asset != payment.asset or network != payment.network or recipient != payment.payment_address: raise PaymentProviderError("crypto_payment_verification_failed")
        if expired: raise PaymentProviderError("crypto_payment_expired")
        if confirmations < required_confirmations: raise PaymentProviderError("crypto_confirmations_insufficient")
        try: received = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc: raise PaymentProviderError("crypto_amount_invalid") from exc
        if received != payment.amount: raise PaymentProviderError("crypto_amount_mismatch")
        return True
    def normalize_event(self, event):
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str) or not isinstance(event.get("status"), str): raise PaymentProviderError("crypto_event_invalid")
        return {"event_id": event["event_id"], "event_type": "CRYPTO_PAYMENT_" + event["status"].upper(), "provider": self.provider, "reference": event.get("reference", "")}
