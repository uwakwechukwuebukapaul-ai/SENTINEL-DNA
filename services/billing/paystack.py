import hashlib, hmac, json
from urllib.parse import urlparse
import requests
from .exceptions import BillingConfigurationError, PaymentProviderError
from .models import PaymentInitialization, PaymentStatus, PaymentVerificationResult
class PaystackPaymentProvider:
    def __init__(self, *, base_url, secret_provider, secret_reference, callback_url, transport=None):
        parsed=urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or not callback_url.startswith("https://"): raise BillingConfigurationError("paystack_https_required")
        self.base_url=base_url.rstrip("/"); self.secret=secret_provider.get(secret_reference) if secret_reference else ""; self.callback_url=callback_url; self.transport=transport or requests
        if not self.secret: raise BillingConfigurationError("paystack_secret_unavailable")
    def _request(self, method, path, **kwargs):
        response=getattr(self.transport, method)(self.base_url+path, headers={"Authorization":"Bearer "+self.secret,"Content-Type":"application/json"}, timeout=10, allow_redirects=False, **kwargs)
        if response.status_code != 200: raise PaymentProviderError("paystack_request_failed")
        try: data=response.json()
        except Exception as exc: raise PaymentProviderError("paystack_response_invalid") from exc
        if not isinstance(data, dict) or not data.get("status") or not isinstance(data.get("data"),dict): raise PaymentProviderError("paystack_response_invalid")
        return data["data"]
    def initialize_payment(self, *, email, reference, amount_minor, currency, callback_url):
        if callback_url != self.callback_url or amount_minor < 0: raise PaymentProviderError("billing_parameters_invalid")
        data=self._request("post","/transaction/initialize",json={"email":email,"amount":amount_minor,"currency":currency,"reference":reference,"callback_url":self.callback_url})
        if not isinstance(data.get("authorization_url"),str): raise PaymentProviderError("paystack_response_invalid")
        return PaymentInitialization("",reference,"",amount_minor,currency,data["authorization_url"])
    def verify_payment(self, reference):
        data=self._request("get",f"/transaction/verify/{reference}")
        status={"success":PaymentStatus.SUCCESS,"failed":PaymentStatus.FAILED,"abandoned":PaymentStatus.CANCELLED}.get(data.get("status"),PaymentStatus.PENDING)
        return PaymentVerificationResult(reference,str(data.get("id","")),status,int(data.get("amount",0)),str(data.get("currency","")),data.get("paid_at"))
    def verify_webhook(self, signature, body):
        return bool(signature) and hmac.compare_digest(hmac.new(self.secret.encode(),body,hashlib.sha512).hexdigest(),signature)
