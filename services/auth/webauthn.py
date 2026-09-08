"""WebAuthn credential lifecycle service.

Cryptographic ceremony verification is delegated to the vetted ``webauthn``
package. This module owns challenge binding, credential persistence, replay
protection, and lifecycle state.
"""
from __future__ import annotations

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse


class WebAuthnError(ValueError):
    pass


class WebAuthnConfiguration:
    """Explicit relying-party configuration; no localhost defaults in production."""

    def __init__(self, rp_id: str, rp_origin: str, rp_name: str, verifier: Any = None):
        self.rp_id, self.rp_origin, self.rp_name, self.verifier = rp_id.strip(), rp_origin.strip(), rp_name.strip(), verifier

    @classmethod
    def from_environment(cls, environ=None):
        values = environ or os.environ
        return cls(values.get("SENTINEL_DNA_WEBAUTHN_RP_ID", ""), values.get("SENTINEL_DNA_WEBAUTHN_RP_ORIGIN", ""), values.get("SENTINEL_DNA_WEBAUTHN_RP_NAME", "Sentinel DNA"))

    def validate(self, production: bool = True) -> None:
        parsed = urlparse(self.rp_origin)
        if not self.rp_id or not self.rp_name or parsed.scheme not in {"https"} or not parsed.hostname or parsed.username or parsed.password:
            raise WebAuthnError("webauthn_configuration_invalid")
        if production and parsed.hostname in {"localhost", "127.0.0.1"}:
            raise WebAuthnError("webauthn_origin_untrusted")
        if parsed.hostname != self.rp_id and not parsed.hostname.endswith("." + self.rp_id):
            raise WebAuthnError("webauthn_rp_origin_mismatch")
        if not callable(self.verifier):
            raise WebAuthnError("webauthn_verifier_required")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebAuthnService:
    def __init__(self, db: Any, configuration: WebAuthnConfiguration | None = None):
        self.db, self.configuration = db, configuration

    def create_challenge(self, user_id: int, purpose: str) -> str:
        if self.configuration is not None:
            self.configuration.validate(production=os.getenv("SENTINEL_DNA_ENV", "development").strip().lower() == "production")
        if purpose not in {"registration", "authentication"}:
            raise WebAuthnError("webauthn_purpose_invalid")
        challenge = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()
        expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        with self.db.session() as connection:
            connection.execute("DELETE FROM auth_webauthn_challenges WHERE user_id=? AND purpose=?", (user_id, purpose))
            connection.execute("INSERT INTO auth_webauthn_challenges(user_id,purpose,challenge,created_at,expires_at) VALUES(?,?,?,?,?)", (user_id, purpose, encoded, _now(), expires))
        return encoded

    def consume_challenge(self, user_id: int, purpose: str, challenge: str) -> bool:
        if not challenge or not isinstance(challenge, str):
            return False
        with self.db.session() as connection:
            row = connection.execute("SELECT id,expires_at FROM auth_webauthn_challenges WHERE user_id=? AND purpose=? AND challenge=? AND consumed_at IS NULL", (user_id, purpose, challenge)).fetchone()
            if not row:
                return False
            try:
                if datetime.fromisoformat(str(row["expires_at"])) <= datetime.now(timezone.utc):
                    return False
            except (TypeError, ValueError):
                return False
            connection.execute("UPDATE auth_webauthn_challenges SET consumed_at=? WHERE id=?", (_now(), row["id"]))
        return True

    def register_credential(self, user_id: int, credential_id: str, public_key: str, sign_count: int = 0) -> None:
        if not credential_id.strip() or not public_key.strip() or sign_count < 0:
            raise WebAuthnError("webauthn_credential_invalid")
        with self.db.session() as connection:
            connection.execute("INSERT INTO auth_webauthn_credentials(user_id,credential_id,public_key,sign_count,created_at) VALUES(?,?,?,?,?)", (user_id, credential_id, public_key, sign_count, _now()))

    def update_sign_count(self, user_id: int, credential_id: str, sign_count: int) -> bool:
        if sign_count < 0: raise WebAuthnError("webauthn_sign_count_invalid")
        with self.db.session() as connection:
            row = connection.execute("SELECT sign_count FROM auth_webauthn_credentials WHERE user_id=? AND credential_id=? AND revoked_at IS NULL", (user_id, credential_id)).fetchone()
            if not row or sign_count <= int(row["sign_count"]): raise WebAuthnError("webauthn_sign_count_replay")
            connection.execute("UPDATE auth_webauthn_credentials SET sign_count=?,last_used_at=? WHERE user_id=? AND credential_id=?", (sign_count, _now(), user_id, credential_id))
        return True

    def credentials_for_user(self, user_id: int) -> list[dict[str, Any]]:
        with self.db.session() as connection:
            rows = connection.execute("SELECT credential_id,sign_count,created_at,last_used_at,revoked_at FROM auth_webauthn_credentials WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def revoke_credential(self, user_id: int, credential_id: str) -> bool:
        with self.db.session() as connection:
            result = connection.execute("UPDATE auth_webauthn_credentials SET revoked_at=? WHERE user_id=? AND credential_id=? AND revoked_at IS NULL", (_now(), user_id, credential_id))
            return result.rowcount == 1
