"""Flask request-local integration for a future trusted provider adapter."""

from __future__ import annotations

from functools import wraps
from flask import g, jsonify, request

from .authentication import CanonicalAuthenticationError, TrustedProviderAdapter


_CONTEXT_KEY = "canonical_request_context"


def canonical_request_context():
    """Return the current request's canonical context, if one was composed."""
    return getattr(g, _CONTEXT_KEY, None)


def require_canonical_authentication(provider_adapter: TrustedProviderAdapter):
    """Protect a route with trusted canonical authentication only.

    The adapter is injected by the application boundary. No request parameter,
    header, cookie, or legacy session value is used as a principal source.
    """
    if provider_adapter is None or not callable(getattr(provider_adapter, "authenticate", None)):
        raise ValueError("trusted_provider_adapter_required")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            try:
                context = provider_adapter.authenticate(request)
            except CanonicalAuthenticationError:
                return jsonify({"error": "canonical_authentication_required"}), 401
            except Exception:
                return jsonify({"error": "canonical_authentication_required"}), 401
            setattr(g, _CONTEXT_KEY, context)
            return view(*args, **kwargs)

        return wrapped
    return decorator

