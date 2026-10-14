"""Provider-neutral email/SMS delivery boundaries."""
from dataclasses import dataclass
from email.message import EmailMessage
import os
import secrets
import smtplib
import ssl

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

class SMTPEmailProvider(EmailProvider):
    """Send verification codes through an explicitly configured TLS SMTP relay."""

    def __init__(self, *, host: str, port: int, from_address: str,
                 username: str = "", password: str = "", security: str = "starttls"):
        self.host = host.strip()
        self.port = int(port)
        self.from_address = from_address.strip()
        self.username = username
        self.password = password
        self.security = security.strip().lower()
        if not self.host or not self.from_address:
            raise RuntimeError("email_provider_not_configured")
        if self.security not in {"starttls", "ssl"}:
            raise RuntimeError("email_provider_security_invalid")
        if bool(self.username) != bool(self.password):
            raise RuntimeError("email_provider_credentials_incomplete")
        if not 1 <= self.port <= 65535:
            raise RuntimeError("email_provider_port_invalid")

    def send_code(self, destination: str, code: str, purpose: str) -> DeliveryResult:
        message = EmailMessage()
        message["Subject"] = "Your Sentinel DNA verification code"
        message["From"] = self.from_address
        message["To"] = destination
        message.set_content(
            "Your Sentinel DNA verification code is: "
            + str(code)
            + "\n\nIf you did not request this code, you can ignore this message."
        )
        try:
            if self.security == "ssl":
                with smtplib.SMTP_SSL(
                    self.host, self.port, timeout=10,
                    context=ssl.create_default_context(),
                ) as client:
                    if self.username:
                        client.login(self.username, self.password)
                    client.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=10) as client:
                    client.ehlo()
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                    if self.username:
                        client.login(self.username, self.password)
                    client.send_message(message)
        except Exception:
            # Never include the destination, OTP, credentials, or provider
            # response in logs or client-visible error details.
            return DeliveryResult(False, failure="email_delivery_failed")
        return DeliveryResult(True, "smtp-" + secrets.token_hex(8))


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
    environment = os.getenv("SENTINEL_DNA_ENV", "development").strip().lower()
    if testing and configured == "test": return TestEmailProvider()
    if configured == "console" and environment not in {"production", "staging"}: return ConsoleEmailProvider()
    if configured == "smtp":
        host = os.getenv("SENTINEL_DNA_SMTP_HOST", "").strip()
        sender = os.getenv("SENTINEL_DNA_EMAIL_FROM", "").strip()
        username = os.getenv("SENTINEL_DNA_SMTP_USERNAME", "")
        password = os.getenv("SENTINEL_DNA_SMTP_PASSWORD", "")
        if not host or not sender or bool(username) != bool(password):
            raise RuntimeError("email_provider_not_configured")
        try:
            port = int(os.getenv("SENTINEL_DNA_SMTP_PORT", "587"))
        except ValueError as exc:
            raise RuntimeError("email_provider_port_invalid") from exc
        return SMTPEmailProvider(
            host=host,
            port=port,
            from_address=sender,
            username=username,
            password=password,
            security=os.getenv("SENTINEL_DNA_SMTP_SECURITY", "starttls"),
        )
    if configured == "production":
        raise RuntimeError("production_email_provider_adapter_required")
    if environment in {"production", "staging"}:
        raise RuntimeError("production_email_provider_required")
    raise RuntimeError("email_provider_not_configured")

def sms_provider(*, testing=False):
    configured = os.getenv("SENTINEL_DNA_SMS_PROVIDER", "").strip().lower()
    if testing and configured == "test": return TestSMSProvider()
    if configured == "console" and os.getenv("SENTINEL_DNA_ENV", "development") != "production": return TestSMSProvider()
    if configured == "production": raise RuntimeError("production_sms_provider_adapter_required")
    if os.getenv("SENTINEL_DNA_ENV", "development") == "production": raise RuntimeError("production_sms_provider_required")
    raise RuntimeError("sms_provider_not_configured")
