"""Server-enforced TOTP MFA for accounts with an MFA-required policy."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Callable

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, jsonify, request, session

from database.connection import DatabaseConnection, database


MFA_SESSION_TTL = timedelta(hours=12)
MFA_TOTP_INTERVAL = 30
MFA_ISSUER = "Sentinel DNA"
MFA_ALLOWED_PATHS = frozenset(
    {
        "/api/auth/csrf",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/mfa/enroll",
        "/api/auth/mfa/verify-enrollment",
        "/api/auth/mfa/verify",
        "/api/auth/password-reset/request",
        "/api/auth/password-reset/confirm",
    }
)


class MFAError(ValueError):
    """Raised for fail-closed MFA state or verification failures."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MFAService:
    """Persist encrypted TOTP state and server-bound MFA sessions."""

    def __init__(
        self,
        db: DatabaseConnection | None = None,
        *,
        secret_key_provider: Callable[[], str],
        audit_service=None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.db = db or database
        self.secret_key_provider = secret_key_provider
        self.audit_service = audit_service
        self.clock = clock
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mfa_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    session_version INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_mfa_sessions_user_active "
                "ON mfa_sessions(user_id, revoked_at, expires_at)"
            )

    def _fernet(self) -> Fernet:
        secret_key = str(self.secret_key_provider() or "")
        if len(secret_key.strip()) < 32:
            raise MFAError("mfa_encryption_key_unavailable")
        material = hashlib.sha256(
            ("sentinel-dna:mfa-totp:" + secret_key).encode("utf-8")
        ).digest()
        return Fernet(base64.urlsafe_b64encode(material))

    def _encrypt(self, secret: str) -> str:
        return self._fernet().encrypt(secret.encode("utf-8")).decode("ascii")

    def _decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet().decrypt(str(ciphertext).encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeError, MFAError) as exc:
            raise MFAError("mfa_secret_unavailable") from exc

    @staticmethod
    def _hash_session_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _audit(self, event_type: str, *, user_id: int, outcome: str, reason: str | None = None) -> None:
        if self.audit_service is None:
            return
        self.audit_service.record(
            event_type,
            user_id=user_id,
            actor_id=session.get("actor_id"),
            tenant_id=session.get("organization_id"),
            details={"method": "totp", "outcome": outcome, **({"reason": reason} if reason else {})},
        )

    def required(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT mfa_required FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        return bool(row and int(row["mfa_required"] or 0) == 1)

    def _user_row(self, user_id: int):
        with self.db.session() as connection:
            return connection.execute(
                "SELECT id, username, email, is_active, revocation_status, "
                "expires_at, tenant_id, actor_id, session_version, "
                "mfa_required, mfa_secret_ciphertext, mfa_enrolled_at, "
                "mfa_last_counter FROM users WHERE id=?",
                (user_id,),
            ).fetchone()

    def start_enrollment(self, user_id: int) -> str:
        row = self._user_row(user_id)
        if not row or not row["is_active"] or str(row["revocation_status"] or "active") != "active":
            raise MFAError("mfa_account_inactive")
        if not int(row["mfa_required"] or 0):
            raise MFAError("mfa_not_required")
        if row["mfa_enrolled_at"]:
            raise MFAError("mfa_already_enrolled")
        secret = pyotp.random_base32()
        encrypted = self._encrypt(secret)
        with self.db.session() as connection:
            connection.execute(
                "UPDATE users SET mfa_secret_ciphertext=?, mfa_enrolled_at=NULL, "
                "mfa_last_counter=NULL WHERE id=? AND mfa_required=1 "
                "AND mfa_enrolled_at IS NULL",
                (encrypted, user_id),
            )
        self._audit("mfa_enrollment_initiated", user_id=user_id, outcome="success")
        return pyotp.TOTP(secret, interval=MFA_TOTP_INTERVAL).provisioning_uri(
            name=str(row["email"]), issuer_name=MFA_ISSUER
        )

    def _matching_counter(self, secret: str, code: str) -> int | None:
        normalized = str(code or "").strip()
        if len(normalized) != 6 or not normalized.isdigit():
            return None
        totp = pyotp.TOTP(secret, interval=MFA_TOTP_INTERVAL)
        current = int(self.clock().timestamp()) // MFA_TOTP_INTERVAL
        # A one-step clock-skew window is bounded and replay-protected below.
        for counter in (current - 1, current, current + 1):
            expected = totp.at(counter * MFA_TOTP_INTERVAL)
            if hmac.compare_digest(expected, normalized):
                return counter
        return None

    def _issue_server_session(self, row, *, counter: int) -> str:
        token = secrets.token_urlsafe(32)
        now = self.clock().astimezone(timezone.utc)
        expires = now + MFA_SESSION_TTL
        with self.db.session() as connection:
            connection.execute(
                "INSERT INTO mfa_sessions(token_hash,user_id,session_version,tenant_id,created_at,expires_at) "
                "VALUES(?,?,?,?,?,?)",
                (
                    self._hash_session_token(token),
                    row["id"],
                    int(row["session_version"] or 0),
                    str(row["tenant_id"] or ""),
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
        return token

    def _complete(self, user_id: int, code: str, *, enrollment: bool) -> str:
        row = self._user_row(user_id)
        if not row or not row["is_active"] or str(row["revocation_status"] or "active") != "active":
            raise MFAError("mfa_account_inactive")
        if not int(row["mfa_required"] or 0):
            raise MFAError("mfa_not_required")
        if not row["mfa_secret_ciphertext"]:
            raise MFAError("mfa_enrollment_required")
        if enrollment and row["mfa_enrolled_at"]:
            raise MFAError("mfa_already_enrolled")
        if not enrollment and not row["mfa_enrolled_at"]:
            raise MFAError("mfa_enrollment_required")
        secret = self._decrypt(row["mfa_secret_ciphertext"])
        counter = self._matching_counter(secret, code)
        if counter is None:
            self._audit("mfa_enrollment_failed" if enrollment else "mfa_verification_failed", user_id=user_id, outcome="failure", reason="invalid_code")
            raise MFAError("mfa_code_invalid")
        previous = row["mfa_last_counter"]
        if previous is not None and counter <= int(previous):
            self._audit("mfa_enrollment_failed" if enrollment else "mfa_verification_failed", user_id=user_id, outcome="failure", reason="replayed_code")
            raise MFAError("mfa_code_replayed")
        now = self.clock().astimezone(timezone.utc).isoformat()
        with self.db.session() as connection:
            updated = connection.execute(
                "UPDATE users SET mfa_enrolled_at=COALESCE(mfa_enrolled_at,?), "
                "mfa_last_counter=? WHERE id=? AND mfa_required=1 "
                "AND is_active=1 AND COALESCE(revocation_status,'active')='active' "
                "AND (mfa_last_counter IS NULL OR mfa_last_counter<?)",
                (now, counter, user_id, counter),
            )
            if updated.rowcount != 1:
                raise MFAError("mfa_code_replayed")
        row = self._user_row(user_id)
        token = self._issue_server_session(row, counter=counter)
        self._audit("mfa_enrollment_completed" if enrollment else "mfa_verification_succeeded", user_id=user_id, outcome="success")
        return token

    def complete_enrollment(self, user_id: int, code: str) -> str:
        return self._complete(user_id, code, enrollment=True)

    def verify(self, user_id: int, code: str) -> str:
        return self._complete(user_id, code, enrollment=False)

    def session_verified(
        self,
        user_id: int | None,
        token: str | None,
        *,
        session_version: int | None,
        tenant_id: str | None,
    ) -> bool:
        if not user_id or not token or not tenant_id:
            return False
        try:
            presented_version = int(session_version)
        except (TypeError, ValueError):
            return False
        now = self.clock().astimezone(timezone.utc).isoformat()
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT 1 FROM mfa_sessions WHERE token_hash=? AND user_id=? "
                "AND session_version=? AND tenant_id=? AND revoked_at IS NULL "
                "AND expires_at>?",
                (self._hash_session_token(token), user_id, presented_version, str(tenant_id), now),
            ).fetchone()
        return row is not None

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        with self.db.session() as connection:
            connection.execute(
                "UPDATE mfa_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (self.clock().astimezone(timezone.utc).isoformat(), self._hash_session_token(token)),
            )

    def revoke_user_sessions(self, user_id: int, *, connection=None) -> None:
        def revoke(owned_connection):
            owned_connection.execute(
                "UPDATE mfa_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
                (self.clock().astimezone(timezone.utc).isoformat(), user_id),
            )

        if connection is None:
            with self.db.session() as owned_connection:
                revoke(owned_connection)
        else:
            revoke(connection)


def mfa_boundary_response():
    """Return a response when the current request lacks verified MFA."""
    auth = current_app.container.get("auth_service")
    mfa = current_app.container.get("mfa_service")
    user_id = session.get("user_id")
    if auth is None or not user_id:
        return None
    user = auth.session_user(user_id, session.get("session_version"))
    if user is None or not bool(getattr(user, "mfa_required", False)):
        return None
    if mfa is None:
        return jsonify({"error": "mfa_required"}), 401
    if request.path in MFA_ALLOWED_PATHS:
        return None
    context_tenant = session.get("organization_id")
    if not mfa.session_verified(
        user.id,
        session.get("mfa_session_token"),
        session_version=session.get("session_version"),
        tenant_id=context_tenant,
    ):
        try:
            mfa._audit("mfa_required_access_blocked", user_id=user.id, outcome="failure", reason="mfa_required")
        except Exception:
            pass
        return jsonify({"error": "mfa_required"}), 401
    return None


__all__ = ["MFA_ALLOWED_PATHS", "MFAError", "MFAService", "mfa_boundary_response"]
