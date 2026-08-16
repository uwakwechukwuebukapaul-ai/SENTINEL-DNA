"""Injected, provider-neutral crypto verification and bounded reconciliation."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from .events import NormalizedBillingEvent
from .exceptions import BillingError, PaymentProviderError

REASONS = frozenset({"VERIFIED", "PAYMENT_NOT_FOUND", "AMOUNT_MISMATCH", "ASSET_MISMATCH", "NETWORK_MISMATCH", "DESTINATION_MISMATCH", "REFERENCE_MISMATCH", "INSUFFICIENT_CONFIRMATIONS", "EXPIRED", "PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT", "INVALID_PROVIDER_RESPONSE"})
RETRYABLE = frozenset({"PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT"})

@dataclass(frozen=True)
class CryptoVerificationResult:
    payment_intent_id: str
    provider: str
    provider_payment_reference: str | None
    asset: str
    network: str
    destination: str
    observed_amount: Decimal | None
    expected_quoted_amount: Decimal
    confirmation_count: int
    required_confirmations: int
    verification_status: str
    observed_payment_at: datetime | None
    verified_at: datetime
    expired: bool
    reason_code: str

    def __post_init__(self):
        if self.reason_code not in REASONS:
            raise ValueError("crypto_verification_reason_invalid")
        object.__setattr__(self, "observed_amount", None if self.observed_amount is None else Decimal(str(self.observed_amount)))
        object.__setattr__(self, "expected_quoted_amount", Decimal(str(self.expected_quoted_amount)))

def _observation(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("invalid_provider_response")
    allowed = {"provider_payment_reference", "asset", "network", "destination", "amount", "confirmations", "required_confirmations", "status", "observed_payment_at"}
    if not set(value).issubset(allowed):
        raise ValueError("invalid_provider_response")
    return value

class CryptoPaymentVerificationService:
    def __init__(self, repository, transition_service, provider=None, clock=None):
        self.repository, self.transition_service, self.provider = repository, transition_service, provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def verify(self, canonical_context, payment_intent_id, *, allow_terminal=False):
        tenant_id = getattr(canonical_context, "tenant_id", None)
        if not isinstance(tenant_id, str) or not tenant_id:
            raise BillingError("canonical_tenant_context_required")
        with self.repository.transaction() as connection:
            self.repository.tenant_active(connection, tenant_id)
            intent = self.repository.get_crypto_intent(connection, tenant_id, payment_intent_id)
            if not intent: raise BillingError("crypto_payment_intent_not_found")
            if intent["status"] in {"SUCCESS", "FAILED", "CANCELLED"} and not allow_terminal:
                return self.repository.get_crypto_verification(connection, payment_intent_id)
            quote = self.repository.get_crypto_quote(connection, intent["quote_id"], tenant_id)
            if not quote: raise BillingError("crypto_quote_unavailable")
            expires = datetime.fromisoformat(intent["payment_expires_at"])
            now = self.clock()
            if now >= expires:
                result = self._result(intent, quote, None, now, "EXPIRED", True)
                self.repository.update_crypto_intent(connection, payment_intent_id, "CANCELLED", result)
                self.repository.update_transaction(connection, intent["transaction_reference"], "CANCELLED")
                return result
            if not self.provider: raise BillingError("crypto_verification_provider_unavailable")
            try:
                raw = self.provider.verify_payment_intent(intent=intent, quote=quote)
                data = _observation(raw)
            except (TimeoutError, PaymentProviderError) as exc:
                code = "PROVIDER_TIMEOUT" if "timeout" in str(exc).lower() else "PROVIDER_UNAVAILABLE"
                return self._result(intent, quote, None, now, code, False)
            except Exception:
                return self._result(intent, quote, None, now, "INVALID_PROVIDER_RESPONSE", False)
            reason, status = self._compare(intent, quote, data)
            result = self._result(intent, quote, data, now, reason, False)
            if reason == "VERIFIED":
                event = NormalizedBillingEvent(intent["provider"], "crypto:" + payment_intent_id, "CRYPTO_PAYMENT_VERIFIED", tenant_id, intent["transaction_reference"], transaction_status="SUCCESS")
                self.repository.update_crypto_intent(connection, payment_intent_id, "VERIFIED", result)
                self.repository.update_transaction(connection, intent["transaction_reference"], "SUCCESS", data.get("provider_payment_reference"))
                self.repository.record_event(connection, event.provider_event_id, event.provider, event.event_type, event.provider_transaction_reference)
            elif reason in {"AMOUNT_MISMATCH", "ASSET_MISMATCH", "NETWORK_MISMATCH", "DESTINATION_MISMATCH", "REFERENCE_MISMATCH", "PAYMENT_NOT_FOUND", "INVALID_PROVIDER_RESPONSE"}:
                self.repository.update_crypto_intent(connection, payment_intent_id, "FAILED", result)
                self.repository.update_transaction(connection, intent["transaction_reference"], "FAILED")
            else:
                self.repository.update_crypto_intent(connection, payment_intent_id, status, result)
            return result

    def _compare(self, intent, quote, data):
        if data.get("status") in {"not_found", "missing"}: return "PAYMENT_NOT_FOUND", "AWAITING_PAYMENT"
        try: amount = Decimal(str(data.get("amount")))
        except (InvalidOperation, TypeError, ValueError): return "INVALID_PROVIDER_RESPONSE", "FAILED"
        if amount != Decimal(str(quote["crypto_amount"])): return "AMOUNT_MISMATCH", "FAILED"
        for key, reason in (("asset", "ASSET_MISMATCH"), ("network", "NETWORK_MISMATCH"), ("destination", "DESTINATION_MISMATCH")):
            if data.get(key) != intent[key]: return reason, "FAILED"
        if data.get("provider_payment_reference") not in {intent["provider_reference"], intent["transaction_reference"]}: return "REFERENCE_MISMATCH", "FAILED"
        confirmations = int(data.get("confirmations", 0)); required = int(data.get("required_confirmations", 0))
        if confirmations < required: return ("INSUFFICIENT_CONFIRMATIONS", "PAYMENT_DETECTED" if confirmations == 0 else "CONFIRMING")
        return "VERIFIED", "VERIFIED"

    def _result(self, intent, quote, data, now, reason, expired):
        data = data or {}; amount = data.get("amount")
        return CryptoVerificationResult(intent["payment_intent_id"], intent["provider"], data.get("provider_payment_reference"), intent["asset"], intent["network"], intent["destination"], None if amount is None else Decimal(str(amount)), Decimal(str(quote["crypto_amount"])), int(data.get("confirmations", 0)), int(data.get("required_confirmations", 0)), "VERIFIED" if reason == "VERIFIED" else ("CONFIRMING" if reason == "INSUFFICIENT_CONFIRMATIONS" else "FAILED"), None, now, expired, reason)

class CryptoPaymentReconciliationService:
    def __init__(self, verifier, repository): self.verifier, self.repository = verifier, repository
    def reconcile(self, canonical_context, *, payment_intent_ids=None, limit=100):
        if not isinstance(limit, int) or limit <= 0 or limit > 1000: raise BillingError("reconciliation_limit_invalid")
        tenant_id = getattr(canonical_context, "tenant_id", None)
        with self.repository.transaction() as connection:
            ids = payment_intent_ids or [r["payment_intent_id"] for r in self.repository.find_pending_crypto_intents(connection, tenant_id, limit)]
        return [self.verifier.verify(canonical_context, item) for item in ids[:limit]]
