"""Provider-neutral email/SMS delivery boundaries."""
from dataclasses import dataclass
import os
import secrets

@dataclass(frozen=True)
class DeliveryResult:
    accepted: bool
    provider_request_id: str | None = None
    failure: str | None = None

class EmailProvider:
    def send_code(self, destination: str, code: str, purpose: str) -> DeliveryResult:
        raise NotImplementedError

class TestEmailProvider(EmailProvider):
    __test__ = False
    def __init__(self): self.messages: list[dict[str, str]] = []
    def send_code(self, destination, code, purpose):
        self.messages.append({"destination": destination, "code": code, "purpose": purpose})
        return DeliveryResult(True, "test-email-" + secrets.token_hex(8))

class ConsoleEmailProvider(TestEmailProvider):
    pass

class SMSProvider:
    def send_code(self, destination: str, code: str, purpose: str) -> DeliveryResult:
        raise NotImplementedError

class TestSMSProvider(SMSProvider):
    __test__ = False
    def __init__(self): self.messages: list[dict[str, str]] = []
    def send_code(self, destination, code, purpose):
        self.messages.append({"destination": destination, "code": code, "purpose": purpose})
        return DeliveryResult(True, "test-sms-" + secrets.token_hex(8))

def email_provider(*, testing=False):
    configured = os.getenv("SENTINEL_DNA_EMAIL_PROVIDER", "").strip().lower()
    if testing and configured == "test": return TestEmailProvider()
    if configured == "console" and os.getenv("SENTINEL_DNA_ENV", "development") != "production": return ConsoleEmailProvider()
    if configured == "production":
        raise RuntimeError("production_email_provider_adapter_required")
    if os.getenv("SENTINEL_DNA_ENV", "development") == "production":
        raise RuntimeError("production_email_provider_required")
    raise RuntimeError("email_provider_not_configured")

def sms_provider(*, testing=False):
    configured = os.getenv("SENTINEL_DNA_SMS_PROVIDER", "").strip().lower()
    if testing and configured == "test": return TestSMSProvider()
    if configured == "console" and os.getenv("SENTINEL_DNA_ENV", "development") != "production": return TestSMSProvider()
    if configured == "production": raise RuntimeError("production_sms_provider_adapter_required")
    if os.getenv("SENTINEL_DNA_ENV", "development") == "production": raise RuntimeError("production_sms_provider_required")
    raise RuntimeError("sms_provider_not_configured")
