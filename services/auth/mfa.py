"""Small, standards-based TOTP and secret-protection primitives.

The application already owns authentication, sessions, and audit.  This module
only supplies the cryptographic operations needed by that existing boundary.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from urllib.parse import quote

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1
_ENCRYPTION_VERSION = "v1"
_KDF_SALT = b"sentinel-dna-authenticator-secret-v1"
_KDF_INFO = b"sentinel-dna-totp-secret"


def generate_totp_secret() -> str:
    """Generate a 160-bit RFC 4226-compatible base32 secret."""
    raw = __import__("secrets").token_bytes(20)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _secret_bytes(secret: str) -> bytes:
    value = str(secret or "").strip().replace(" ", "").upper()
    if not value:
        raise ValueError("totp_secret_required")
    try:
        return base64.b32decode(value + "=" * (-len(value) % 8), casefold=True)
    except Exception as exc:  # noqa: BLE001 - normalize decoder failures
        raise ValueError("totp_secret_invalid") from exc


def totp_code(secret: str, timestamp: int | float | None = None) -> str:
    """Return the six-digit SHA-1 TOTP for the given 30-second time step."""
    counter = int(time.time() if timestamp is None else timestamp) // TOTP_PERIOD
    message = struct.pack(">Q", counter)
    digest = hmac.new(_secret_bytes(secret), message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, timestamp: int | float | None = None) -> bool:
    """Verify with one adjacent time-step of clock drift and no more."""
    submitted = str(code or "").strip()
    if len(submitted) != TOTP_DIGITS or not submitted.isdigit():
        return False
    now = time.time() if timestamp is None else timestamp
    try:
        candidates = [totp_code(secret, now + (offset * TOTP_PERIOD)) for offset in range(-TOTP_WINDOW, TOTP_WINDOW + 1)]
    except ValueError:
        return False
    return any(hmac.compare_digest(submitted, candidate) for candidate in candidates)


def _encryption_key(application_secret: str) -> bytes:
    secret = str(application_secret or "").encode("utf-8")
    if len(secret) < 32:
        raise ValueError("application_secret_too_short")
    return HKDF(algorithm=SHA256(), length=32, salt=_KDF_SALT, info=_KDF_INFO).derive(secret)


def encrypt_totp_secret(secret: str, application_secret: str) -> str:
    """Encrypt a TOTP secret with an authenticated AES-GCM envelope."""
    nonce = __import__("secrets").token_bytes(12)
    ciphertext = AESGCM(_encryption_key(application_secret)).encrypt(
        nonce, _secret_bytes(secret), _ENCRYPTION_VERSION.encode("ascii")
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"{_ENCRYPTION_VERSION}.{encode(nonce)}.{encode(ciphertext)}"


def decrypt_totp_secret(envelope: str, application_secret: str) -> str:
    """Decrypt and validate an application-owned TOTP secret envelope."""
    try:
        version, nonce_value, ciphertext_value = str(envelope or "").split(".", 2)
        if version != _ENCRYPTION_VERSION:
            raise ValueError("totp_secret_version_invalid")
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        raw = AESGCM(_encryption_key(application_secret)).decrypt(
            decode(nonce_value), decode(ciphertext_value), version.encode("ascii")
        )
        secret = base64.b32encode(raw).decode("ascii").rstrip("=")
        _secret_bytes(secret)
        return secret
    except Exception as exc:  # noqa: BLE001 - callers receive a safe category
        raise ValueError("totp_secret_unavailable") from exc


def provisioning_uri(secret: str, *, account_name: str, issuer: str = "Sentinel DNA") -> str:
    """Build the standard otpauth URI without adding a QR dependency."""
    account = str(account_name or "").strip()
    if not account:
        raise ValueError("totp_account_required")
    return (
        f"otpauth://totp/{quote(issuer, safe='')}:{quote(account, safe='')}"
        f"?secret={quote(str(secret))}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD}"
    )


__all__ = [
    "TOTP_DIGITS", "TOTP_PERIOD", "TOTP_WINDOW", "decrypt_totp_secret",
    "encrypt_totp_secret", "generate_totp_secret", "provisioning_uri",
    "totp_code", "verify_totp",
]
