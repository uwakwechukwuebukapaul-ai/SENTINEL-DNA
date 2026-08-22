"""Notification adapter contracts with no external provider calls."""
from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse


class NotificationAdapter(Protocol):
    name: str

    def deliver(self, *, tenant_id: str, alert: dict, recipient: str | None = None) -> dict: ...


class DeterministicTestNotificationAdapter:
    name = "deterministic-test"

    def deliver(self, *, tenant_id: str, alert: dict, recipient: str | None = None) -> dict:
        return {"status": "simulated", "adapter": self.name, "tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "recipient": recipient}


class DeterministicEmailNotificationAdapter(DeterministicTestNotificationAdapter):
    name = "email"


class DeterministicSlackNotificationAdapter(DeterministicTestNotificationAdapter):
    name = "slack"


class DeterministicTeamsNotificationAdapter(DeterministicTestNotificationAdapter):
    name = "teams"


class DeterministicWebhookNotificationAdapter(DeterministicTestNotificationAdapter):
    name = "webhook"

    def deliver(self, *, tenant_id: str, alert: dict, recipient: str | None = None) -> dict:
        parsed = urlparse(str(recipient or ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("unsafe_webhook_destination")
        return {"status": "simulated", "adapter": self.name, "tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "recipient": parsed.netloc, "payload_size": min(1024, len(str(alert)))}
