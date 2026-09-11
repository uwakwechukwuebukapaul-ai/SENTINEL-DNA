"""Provider-neutral email/SMS delivery boundaries.

The application never falls back to a local/console mail sink outside tests.
Staging and production must use an explicitly configured SMTP relay.
"""
from dataclasses import dataclass
from email.message import EmailMessage
import os
from pathlib import Path
import secrets
import smtplib

@dataclass(frozen=True)
class DeliveryResult:
    accepted: bool
    provider_request_id: str | None = None
    failure: str | None = None

class EmailProvider:
    def send_code(self, destination: str, code: str, purpose: str) -> DeliveryResult:
        raise NotImplementedError


class SMTPEmailProvider(EmailProvider):
    """Deliver verification mail through an operator-configured SMTP relay."""

    def __init__(self, *, host: str, port: int, username: str, password: str,
                 sender: str, starttls: bool = True, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.starttls = starttls
        self.timeout = timeout

    @classmethod
    def from_environment(cls):
        def configured(name: str, *, strip: bool = True) -> str:
            direct = os.getenv(name)
            secret_file = os.getenv(f"{name}_FILE", "").strip()
            if direct is not None and secret_file:
                raise RuntimeError(f"smtp_configuration_ambiguous:{name}")
            if secret_file:
                try:
                    value = Path(secret_file).read_text(encoding="utf-8").strip()
                except (OSError, UnicodeError) as exc:
                    raise RuntimeError(f"smtp_configuration_secret_file_unreadable:{name}") from exc
                return value
            value = direct or ""
            return value.strip() if strip else value

        required = {
            "SENTINEL_DNA_SMTP_HOST": os.getenv("SENTINEL_DNA_SMTP_HOST", "").strip(),
            "SENTINEL_DNA_SMTP_USERNAME": configured("SENTINEL_DNA_SMTP_USERNAME"),
            "SENTINEL_DNA_SMTP_PASSWORD": configured("SENTINEL_DNA_SMTP_PASSWORD", strip=False),
            "SENTINEL_DNA_EMAIL_FROM": os.getenv("SENTINEL_DNA_EMAIL_FROM", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("smtp_configuration_incomplete:" + ",".join(missing))
        try:
            port = int(os.getenv("SENTINEL_DNA_SMTP_PORT", "587"))
            timeout = float(os.getenv("SENTINEL_DNA_SMTP_TIMEOUT", "10"))
        except ValueError as exc:
            raise RuntimeError("smtp_configuration_invalid") from exc
        if not 1 <= port <= 65535 or timeout <= 0:
            raise RuntimeError("smtp_configuration_invalid")
        return cls(
            host=required["SENTINEL_DNA_SMTP_HOST"], port=port,
            username=required["SENTINEL_DNA_SMTP_USERNAME"],
            password=required["SENTINEL_DNA_SMTP_PASSWORD"],
            sender=required["SENTINEL_DNA_EMAIL_FROM"],
            starttls=os.getenv("SENTINEL_DNA_SMTP_STARTTLS", "1").strip().lower() in {"1", "true", "yes"},
            timeout=timeout,
        )

    def send_code(self, destination, code, purpose):
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = destination
        message["Subject"] = "Sentinel DNA verification code"
        message.set_content(
            f"Your Sentinel DNA {purpose.replace('_', ' ')} code is {code}. "
            "It expires shortly and must not be shared."
        )
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as client:
            client.ehlo()
            if self.starttls:
                client.starttls()
                client.ehlo()
            client.login(self.username, self.password)
            client.send_message(message)
        return DeliveryResult(True, "smtp-" + secrets.token_hex(16))

class TestEmailProvider(EmailProvider):
    __test__ = False
    def __init__(self): self.messages: list[dict[str, str]] = []
    def send_code(self, destination, code, purpose):
        self.messages.append({"destination": destination, "code": code, "purpose": purpose})
        return DeliveryResult(True, "test-email-" + secrets.token_hex(8))

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
    if configured != "smtp":
        raise RuntimeError("smtp_email_provider_required")
    return SMTPEmailProvider.from_environment()


def validate_email_provider_configuration() -> None:
    """Validate mail configuration without connecting to the relay."""
    if os.getenv("SENTINEL_DNA_ENV", "development").strip().lower() == "testing":
        return
    email_provider()

def sms_provider(*, testing=False):
    configured = os.getenv("SENTINEL_DNA_SMS_PROVIDER", "").strip().lower()
    if testing and configured == "test": return TestSMSProvider()
    if configured == "console" and os.getenv("SENTINEL_DNA_ENV", "development") != "production": return TestSMSProvider()
    if configured == "production": raise RuntimeError("production_sms_provider_adapter_required")
    if os.getenv("SENTINEL_DNA_ENV", "development") == "production": raise RuntimeError("production_sms_provider_required")
    raise RuntimeError("sms_provider_not_configured")
