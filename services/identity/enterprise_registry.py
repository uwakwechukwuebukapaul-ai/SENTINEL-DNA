"""Runtime registry for configured enterprise identity providers."""
from __future__ import annotations

import os
from collections.abc import Mapping

from .entra_oidc import (
    EntraEnterpriseFlow,
    EntraOidcConfig,
    EntraOidcError,
    ExternalSecretReferenceResolver,
)


def load_enterprise_oidc_registry(environ: Mapping[str, str] | None = None) -> dict:
    """Load only explicitly enabled, fully configured provider flows.

    This function performs no provisioning and never stores a secret. The
    secret reference is resolved only by the flow when its health check or
    token exchange executes.
    """
    values = os.environ if environ is None else environ
    if str(values.get("SENTINEL_DNA_ENTRA_OIDC_ENABLED", "0")).strip() != "1":
        return {}
    try:
        config = EntraOidcConfig.from_environment(values)
        config.validate()
        return {
            "entra": EntraEnterpriseFlow(
                config,
                secret_resolver=ExternalSecretReferenceResolver(values),
            )
        }
    except (EntraOidcError, ValueError, TypeError):
        return {}
