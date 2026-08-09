"""
Sentinel DNA Connector Framework.

Provides security platform integrations
for automated response actions.
"""

from .base_connector import BaseConnector
from .firewall_connector import FirewallConnector
from .endpoint_connector import EndpointConnector
from .email_connector import EmailConnector
from .identity_connector import IdentityConnector


__all__ = [
    "BaseConnector",
    "FirewallConnector",
    "EndpointConnector",
    "EmailConnector",
    "IdentityConnector",
]