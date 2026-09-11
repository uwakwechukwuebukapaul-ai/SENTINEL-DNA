"""Non-secret authentication provider readiness projection."""
from __future__ import annotations

import os
from typing import Mapping


def authentication_provider_readiness(environ: Mapping[str, str] | None = None) -> dict[str, object]:
    """Return presence-only readiness facts; never return configuration values."""
    values = os.environ if environ is None else environ
    google = all(values.get(name, "").strip() for name in (
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
    ))
    sms_selection = values.get("SENTINEL_DNA_SMS_PROVIDER", "").strip().lower()
    return {
        "google_legacy_compatibility": {"configured": google, "enabled": google},
        "sms_recovery": {
            "configured": bool(sms_selection),
            "implemented": False,
            "enabled": False,
            "reason": "sms_recovery_not_approved",
        },
    }
