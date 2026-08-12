"""Stripe adapter for the provider-neutral billing boundary."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any
from urllib import parse, request

from sentinel_dna.saas.billing import BillingConfigurationError, BillingPlan


class StripeSignatureError(PermissionError):
    pass


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str
    webhook_secret: str
    price_ids: dict[str, str]
    success_url: str = "https://sentinel-dna.local/billing/success"
    cancel_url: str = "https://sentinel-dna.local/billing/cancel"

    def __post_init__(self) -> None:
        if not self.secret_key or not self.webhook_secret or not self.price_ids:
            raise BillingConfigurationError("Stripe configuration is incomplete")


class StripeProvider:
    provider_name = "stripe"

    def __init__(self, config: StripeConfig, http_client: Any | None = None) -> None:
        self.config = config
        self.http_client = http_client

    def create_customer(self, tenant_id: str, billing_email: str, idempotency_key: str) -> dict[str, Any]:
        return self._post(
            "/v1/customers",
            {"email": billing_email, "metadata[tenant_id]": tenant_id},
            idempotency_key,
        )

    def create_checkout_session(self, tenant_id: str, plan: BillingPlan, idempotency_key: str) -> dict[str, Any]:
        price_id = self.config.price_ids.get(plan.plan_id)
        if not price_id:
            raise BillingConfigurationError("Stripe price is not configured for plan")
        return self._post(
            "/v1/checkout/sessions",
            {
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "client_reference_id": tenant_id,
                "metadata[tenant_id]": tenant_id,
                "metadata[plan_id]": plan.plan_id,
                "subscription_data[metadata][tenant_id]": tenant_id,
                "subscription_data[metadata][plan_id]": plan.plan_id,
                "success_url": self.config.success_url,
                "cancel_url": self.config.cancel_url,
            },
            idempotency_key,
        )

    def retrieve_subscription(self, provider_subscription_id: str) -> dict[str, Any]:
        return self._get(f"/v1/subscriptions/{parse.quote(provider_subscription_id)}")

    def cancel_subscription(self, provider_subscription_id: str, idempotency_key: str) -> dict[str, Any]:
        return self._delete(f"/v1/subscriptions/{parse.quote(provider_subscription_id)}", idempotency_key)

    def retrieve_invoices(self, provider_customer_id: str) -> list[dict[str, Any]]:
        payload = self._get(f"/v1/invoices?customer={parse.quote(provider_customer_id)}")
        return list(payload.get("data", []))

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not signature:
            raise StripeSignatureError("missing Stripe signature")
        parts = dict(item.split("=", 1) for item in signature.split(",") if "=" in item)
        timestamp = parts.get("t")
        expected = parts.get("v1")
        if not timestamp or not expected:
            raise StripeSignatureError("invalid Stripe signature header")
        if abs(int(time.time()) - int(timestamp)) > 300:
            raise StripeSignatureError("stale Stripe signature")
        signed_payload = f"{timestamp}.".encode("utf-8") + payload
        digest = hmac.new(self.config.webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, expected):
            raise StripeSignatureError("invalid Stripe signature")
        event = json.loads(payload.decode("utf-8"))
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise StripeSignatureError("invalid Stripe event")
        return event

    def _post(self, path: str, data: dict[str, str], idempotency_key: str) -> dict[str, Any]:
        if self.http_client:
            return self.http_client.post(path, data, idempotency_key)
        return self._request("POST", path, data, idempotency_key)

    def _delete(self, path: str, idempotency_key: str) -> dict[str, Any]:
        if self.http_client:
            return self.http_client.delete(path, idempotency_key)
        return self._request("DELETE", path, {}, idempotency_key)

    def _get(self, path: str) -> dict[str, Any]:
        if self.http_client:
            return self.http_client.get(path)
        return self._request("GET", path, None, None)

    def _request(self, method: str, path: str, data: dict[str, str] | None, idempotency_key: str | None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.config.secret_key}"}
        body = None
        if data is not None:
            body = parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request_object = request.Request(f"https://api.stripe.com{path}", data=body, headers=headers, method=method)
        with request.urlopen(request_object, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
