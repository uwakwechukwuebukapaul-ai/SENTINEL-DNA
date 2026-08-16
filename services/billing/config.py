from dataclasses import dataclass
import os
from urllib.parse import urlparse
from .exceptions import BillingConfigurationError
@dataclass(frozen=True)
class BillingConfiguration:
    enabled: bool=False; base_url: str="https://api.paystack.co"; public_key: str=""; secret_key_reference: str=""; webhook_secret_reference: str=""; callback_url: str=""; timeout_seconds: float=10.0; currency: str="NGN"
    @classmethod
    def from_environment(cls, environ=None):
        e=environ or os.environ; return cls(e.get("PAYSTACK_ENABLED","false").lower()=="true",e.get("PAYSTACK_BASE_URL","https://api.paystack.co"),e.get("PAYSTACK_PUBLIC_KEY",""),e.get("PAYSTACK_SECRET_KEY_REFERENCE",""),e.get("PAYSTACK_WEBHOOK_SECRET_REFERENCE",e.get("PAYSTACK_SECRET_KEY_REFERENCE","")),e.get("PAYSTACK_CALLBACK_URL",""),float(e.get("PAYSTACK_TIMEOUT_SECONDS","10")),e.get("PAYSTACK_CURRENCY","NGN"))
    def reason_codes(self):
        if not self.enabled: return ("PAYSTACK_DISABLED",)
        parsed=urlparse(self.base_url); callback=urlparse(self.callback_url)
        if parsed.scheme != "https" or parsed.netloc not in {"api.paystack.co", "api.paystack.test", "api.test"} or parsed.path not in ("", "/") or parsed.query or parsed.fragment: return ("PAYSTACK_CONFIGURATION_INVALID",)
        if callback.scheme != "https" or not callback.netloc or callback.username or callback.password or callback.fragment: return ("PAYSTACK_CONFIGURATION_INVALID",)
        if not self.secret_key_reference or not self.webhook_secret_reference: return ("PAYSTACK_SECRET_REFERENCE_MISSING",)
        if not self.callback_url or self.timeout_seconds <= 0 or self.timeout_seconds > 30 or self.currency != "NGN": return ("PAYSTACK_CONFIGURATION_INCOMPLETE",)
        return ("PAYSTACK_READY",)
    def validate(self):
        reasons=self.reason_codes()
        if reasons == ("PAYSTACK_DISABLED",): return False
        if reasons != ("PAYSTACK_READY",): raise BillingConfigurationError("paystack_configuration_invalid")
        return True


class EnvironmentSecretProvider:
    """Resolve deployment-managed secret references without exposing values."""
    def __init__(self, environ=None): self.environ = environ or os.environ
    def get(self, reference):
        reference=str(reference or "").strip()
        if not reference or reference not in self.environ: return ""
        return self.environ.get(reference, "")
