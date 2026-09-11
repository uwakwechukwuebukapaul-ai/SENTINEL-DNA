"""Validate the external Entra staging configuration without printing secrets."""
from __future__ import annotations

import argparse
import sys

from services.identity.entra_oidc import EntraDiscovery, EntraOidcConfig, EntraOidcError, ExternalSecretReferenceResolver


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Sentinel DNA staging Entra OIDC configuration")
    parser.add_argument("--check-discovery", action="store_true", help="also validate Entra discovery metadata over HTTPS")
    args = parser.parse_args()
    try:
        config = EntraOidcConfig.from_environment()
        config.validate()
        if not ExternalSecretReferenceResolver()(config.client_secret_reference):
            raise EntraOidcError("entra_client_secret_reference_unavailable")
        if args.check_discovery:
            EntraDiscovery(config).validate()
    except Exception as exc:
        print(f"Entra OIDC staging check failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("Entra OIDC staging configuration: ready")
    print(f"callback: {config.redirect_uri}")
    print(f"discovery: {'validated' if args.check_discovery else 'not checked (use --check-discovery)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
