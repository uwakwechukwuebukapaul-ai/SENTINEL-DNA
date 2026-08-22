"""Provider-neutral operational notification boundary."""
from .adapters import DeterministicTestNotificationAdapter, DeterministicEmailNotificationAdapter, DeterministicSlackNotificationAdapter, DeterministicTeamsNotificationAdapter, DeterministicWebhookNotificationAdapter, NotificationAdapter
from .service import NotificationService
from .providers import SmtpEmailNotificationAdapter, SlackWebhookNotificationAdapter, TeamsWebhookNotificationAdapter, GenericWebhookNotificationAdapter, configured_provider_adapters
from .secrets import SecretResolver, EnvironmentSecretResolver

__all__ = ["NotificationAdapter", "DeterministicTestNotificationAdapter", "DeterministicEmailNotificationAdapter", "DeterministicSlackNotificationAdapter", "DeterministicTeamsNotificationAdapter", "DeterministicWebhookNotificationAdapter", "NotificationService", "SmtpEmailNotificationAdapter", "SlackWebhookNotificationAdapter", "TeamsWebhookNotificationAdapter", "GenericWebhookNotificationAdapter", "configured_provider_adapters", "SecretResolver", "EnvironmentSecretResolver"]
