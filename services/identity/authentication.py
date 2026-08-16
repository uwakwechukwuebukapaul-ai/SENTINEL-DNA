"""Canonical authentication boundary contract.

The current platform has no canonical credential source. This module defines
the narrow boundary a future trusted authenticator must satisfy; it does not
translate legacy sessions or validate credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .canonical_authority import CanonicalAuthorityError
from .request_context import CanonicalRequestContext, CanonicalRequestContextService


class CanonicalAuthenticationError(ValueError):
    """Raised when a canonical authentication principal is not trustworthy."""


@dataclass(frozen=True)
class AuthenticatedProviderPrincipal:
    """Provider-verified subject handed to the canonical boundary.

    Claims are informational input for future provisioning only. They are not
    canonical identity, membership, role, or authorization state.
    """

    provider: str
    subject: str
    tenant_id: str
    actor_id: str
    authentication_method: str
    credential_id: str
    claims: tuple[tuple[str, str], ...] = ()
    external_subject: str = ""


class TrustedAuthenticationProvider(Protocol):
    """Provider-neutral contract for a future OIDC/SAML adapter."""

    def authenticate(self, request: Any) -> AuthenticatedProviderPrincipal: ...


@dataclass(frozen=True)
class CanonicalAuthenticationPrincipal:
    """Authenticated canonical subject supplied by a trusted authenticator.

    Role, membership, and authority are intentionally absent. They are always
    resolved by the canonical authority domain after authentication.
    """

    tenant_id: str
    actor_id: str
    authentication_method: str
    credential_id: str


class CanonicalAuthenticationBoundary:
    """Convert a trusted canonical principal into a request context."""

    def __init__(self, request_context: CanonicalRequestContextService):
        if request_context is None or not hasattr(request_context, "resolve"):
            raise ValueError("canonical_request_context_required")
        self.request_context = request_context

    def compose(self, principal: CanonicalAuthenticationPrincipal) -> CanonicalRequestContext:
        if not isinstance(principal, CanonicalAuthenticationPrincipal):
            raise CanonicalAuthenticationError("canonical_principal_invalid")
        if not principal.authentication_method.strip() or not principal.credential_id.strip():
            raise CanonicalAuthenticationError("canonical_principal_invalid")
        try:
            return self.request_context.resolve(principal.tenant_id, principal.actor_id)
        except Exception as exc:
            raise CanonicalAuthenticationError("canonical_authentication_denied") from exc


class TrustedProviderAdapter:
    """Bridge a real trusted provider into canonical authentication.

    This adapter deliberately does not implement credentials, tokens, claims
    verification, provisioning, or legacy fallback. Those responsibilities
    belong to a concrete enterprise provider adapter selected later.
    """

    SUPPORTED_METHODS = {"oidc", "saml", "service_account"}

    def __init__(self, provider: TrustedAuthenticationProvider, boundary: CanonicalAuthenticationBoundary, bindings=None):
        if provider is None or not callable(getattr(provider, "authenticate", None)):
            raise ValueError("trusted_authentication_provider_required")
        self.provider = provider
        self.boundary = boundary
        self.bindings = bindings

    def authenticate(self, request: Any) -> CanonicalRequestContext:
        try:
            principal = self.provider.authenticate(request)
        except Exception as exc:
            raise CanonicalAuthenticationError("provider_authentication_failed") from exc
        if not isinstance(principal, AuthenticatedProviderPrincipal):
            raise CanonicalAuthenticationError("provider_principal_invalid")
        if principal.provider.strip() == "" or principal.subject.strip() == "":
            raise CanonicalAuthenticationError("provider_principal_invalid")
        if principal.authentication_method not in self.SUPPORTED_METHODS:
            raise CanonicalAuthenticationError("unsupported_authentication_method")
        if not principal.credential_id.strip():
            raise CanonicalAuthenticationError("provider_principal_invalid")
        actor_id = principal.actor_id
        if self.bindings is not None:
            if not principal.external_subject.strip():
                raise CanonicalAuthenticationError("provider_subject_required")
            try:
                actor_id = self.bindings.resolve(principal.provider, principal.external_subject).actor_id
            except Exception as exc:
                raise CanonicalAuthenticationError("identity_binding_denied") from exc
        canonical = CanonicalAuthenticationPrincipal(
            tenant_id=principal.tenant_id,
            actor_id=actor_id,
            authentication_method=principal.authentication_method,
            credential_id=principal.credential_id,
        )
        return self.boundary.compose(canonical)
