"""Compatibility exports for the enterprise connector foundation."""
from ..base import IntegrationAdapter, MockEnterpriseAdapter
from ..models import Integration, CredentialRef
from ..registry import IntegrationRegistry

__all__ = ["IntegrationAdapter", "MockEnterpriseAdapter", "Integration", "CredentialRef", "IntegrationRegistry"]
