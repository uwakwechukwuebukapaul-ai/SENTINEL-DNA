"""Production-oriented provider adapters with bounded, sanitized delivery."""
from __future__ import annotations

import ipaddress
import json
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .secrets import EnvironmentSecretResolver


def _safe_url(value: str) -> tuple:
    parsed = urlparse(str(value or ""))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("unsafe_webhook_destination")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local") or host.endswith(".internal"):
        raise ValueError("unsafe_webhook_destination")
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise ValueError("unsafe_webhook_destination")
    except ValueError as exc:
        if str(exc) == "unsafe_webhook_destination":
            raise
    return parsed, host


def _payload(alert: dict) -> bytes:
    safe = {key: alert.get(key) for key in ("alert_id", "rule", "severity", "reason", "metric_source", "observed_value", "threshold", "detected_at")}
    body = json.dumps(safe, sort_keys=True, default=str).encode("utf-8")
    if len(body) > 16 * 1024:
        raise ValueError("notification_payload_too_large")
    return body


class SmtpEmailNotificationAdapter:
    name = "email"

    def __init__(self, *, host: str, port: int = 587, username: str | None = None, password_reference: str | None = None, sender: str, resolver=None, timeout: int = 10, use_tls: bool = True):
        self.host, self.port, self.username, self.password_reference, self.sender = str(host), int(port), username, password_reference, str(sender)
        self.resolver, self.timeout, self.use_tls = resolver or EnvironmentSecretResolver(), min(30, max(1, int(timeout))), bool(use_tls)

    def deliver(self, *, tenant_id: str, alert: dict, recipient: str | None = None) -> dict:
        if not recipient or "@" not in str(recipient):
            raise ValueError("invalid_notification_destination")
        message = EmailMessage(); message["Subject"] = f"Sentinel DNA operational alert {alert.get('alert_id', '')}"; message["From"] = self.sender; message["To"] = str(recipient); message.set_content(_payload(alert).decode("utf-8"))
        password = self.resolver.resolve(self.password_reference) if self.password_reference else None
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
            if self.use_tls: smtp.starttls()
            if self.username: smtp.login(self.username, password or "")
            smtp.send_message(message)
        return {"status": "delivered", "adapter": self.name, "tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "recipient_domain": str(recipient).split("@", 1)[-1]}


class HttpsWebhookNotificationAdapter:
    def __init__(self, *, name: str, resolver=None, secret_reference: str | None = None, timeout: int = 10):
        self.name, self.resolver, self.secret_reference, self.timeout = name, resolver or EnvironmentSecretResolver(), secret_reference, min(30, max(1, int(timeout)))

    def deliver(self, *, tenant_id: str, alert: dict, recipient: str | None = None) -> dict:
        parsed, host = _safe_url(recipient or "")
        headers = {"Content-Type": "application/json"}
        if self.secret_reference:
            headers["Authorization"] = f"Bearer {self.resolver.resolve(self.secret_reference)}"
        request = Request(str(parsed.geturl()), data=_payload(alert), headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = int(getattr(response, "status", 200))
        except TimeoutError as exc:
            raise ConnectionError("notification_provider_timeout") from exc
        except OSError as exc:
            raise ConnectionError("notification_provider_unavailable") from exc
        return {"status": "delivered", "adapter": self.name, "tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "destination_host": host, "http_status": status}


class SlackWebhookNotificationAdapter(HttpsWebhookNotificationAdapter):
    def __init__(self, **kwargs): super().__init__(name="slack", **kwargs)


class TeamsWebhookNotificationAdapter(HttpsWebhookNotificationAdapter):
    def __init__(self, **kwargs): super().__init__(name="teams", **kwargs)


class GenericWebhookNotificationAdapter(HttpsWebhookNotificationAdapter):
    def __init__(self, **kwargs): super().__init__(name="webhook", **kwargs)


def configured_provider_adapters(*, resolver=None):
    """Build production adapters only when safe configuration is present.

    Routes persist adapter names and secret references, never resolved values.
    Missing configuration intentionally leaves deterministic adapters active.
    """
    resolver = resolver or EnvironmentSecretResolver()
    configured = {}
    smtp_host = os.environ.get("SENTINEL_NOTIFICATION_SMTP_HOST")
    smtp_sender = os.environ.get("SENTINEL_NOTIFICATION_SMTP_SENDER")
    if smtp_host and smtp_sender:
        configured["email"] = SmtpEmailNotificationAdapter(host=smtp_host, port=int(os.environ.get("SENTINEL_NOTIFICATION_SMTP_PORT", "587")), username=os.environ.get("SENTINEL_NOTIFICATION_SMTP_USERNAME"), password_reference=os.environ.get("SENTINEL_NOTIFICATION_SMTP_PASSWORD_REF"), sender=smtp_sender, resolver=resolver)
    if os.environ.get("SENTINEL_NOTIFICATION_SLACK_SECRET_REF"):
        configured["slack"] = SlackWebhookNotificationAdapter(secret_reference=os.environ["SENTINEL_NOTIFICATION_SLACK_SECRET_REF"], resolver=resolver)
    if os.environ.get("SENTINEL_NOTIFICATION_TEAMS_SECRET_REF"):
        configured["teams"] = TeamsWebhookNotificationAdapter(secret_reference=os.environ["SENTINEL_NOTIFICATION_TEAMS_SECRET_REF"], resolver=resolver)
    if os.environ.get("SENTINEL_NOTIFICATION_WEBHOOK_SECRET_REF"):
        configured["webhook"] = GenericWebhookNotificationAdapter(secret_reference=os.environ["SENTINEL_NOTIFICATION_WEBHOOK_SECRET_REF"], resolver=resolver)
    return configured
