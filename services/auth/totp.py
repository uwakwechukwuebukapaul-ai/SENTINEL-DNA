"""Small RFC 6238 TOTP primitive for the Sentinel authentication boundary."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import quote

INTERVAL_SECONDS = 30
DIGITS = 6

def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

def provisioning_uri(secret: str, account: str, issuer: str = "Sentinel DNA") -> str:
    return f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={quote(secret)}&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={INTERVAL_SECONDS}"

def _code(secret: str, counter: int) -> str:
    padded = str(secret).upper() + "=" * (-len(str(secret)) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return f"{value % (10 ** DIGITS):0{DIGITS}d}"

def verify_code(secret: str, submitted: str, *, now: int | None = None, window: int = 1) -> bool:
    value = str(submitted or "").strip()
    if len(value) != DIGITS or not value.isdigit(): return False
    counter = int((time.time() if now is None else now) // INTERVAL_SECONDS)
    return any(hmac.compare_digest(_code(secret, counter + delta), value) for delta in range(-window, window + 1))
