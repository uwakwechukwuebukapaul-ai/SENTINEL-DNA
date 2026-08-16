from dataclasses import dataclass
import os
from urllib.parse import urlparse
from .exceptions import BillingConfigurationError
@dataclass(frozen=True)
class BillingConfiguration:
    enabled: bool=False; base_url: str="https://api.paystack.co"; public_key: str=""; secret_key_reference: str=""; webhook_secret_reference: str=""; callback_url: str=""
    @classmethod
    def from_environment(cls, environ=None):
        e=environ or os.environ; return cls(e.get("PAYSTACK_ENABLED","false").lower()=="true",e.get("PAYSTACK_BASE_URL","https://api.paystack.co"),e.get("PAYSTACK_PUBLIC_KEY",""),e.get("PAYSTACK_SECRET_KEY_REFERENCE",""),e.get("PAYSTACK_WEBHOOK_SECRET_REFERENCE",e.get("PAYSTACK_SECRET_KEY_REFERENCE","")),e.get("PAYSTACK_CALLBACK_URL",""))
    def validate(self):
        if not self.enabled: return False
        if urlparse(self.base_url).scheme != "https" or not self.secret_key_reference or not self.webhook_secret_reference or not self.callback_url.startswith("https://"): raise BillingConfigurationError("paystack_configuration_incomplete")
        return True
