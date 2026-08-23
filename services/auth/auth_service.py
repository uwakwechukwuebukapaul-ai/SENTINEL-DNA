"""SQLite-backed authentication service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from database.connection import DatabaseConnection, database
from .models import User
from .security import hash_password, verify_password
from .age import validate_minimum_age
from .otp import code_hash, expires_at, generate_code, utcnow, OTP_COOLDOWN_SECONDS, OTP_MAX_ATTEMPTS
from .phone import normalize_phone
from .rate_limit import DatabaseRateLimitBackend
from services.rate_limiting import RateLimitPolicy, RateLimitRequest, RateLimitService


class AuthService:
    ROLES = {"admin", "soc_manager", "analyst", "viewer"}

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        with self.db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst', created_at TEXT NOT NULL,
                last_login TEXT, is_active INTEGER NOT NULL DEFAULT 1)""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
            for name in ("phone_number", "phone_verified_at", "tenant_id", "actor_id", "date_of_birth", "email_verified_at"):
                if name not in columns: connection.execute(f"ALTER TABLE users ADD COLUMN {name} TEXT")
            if "session_version" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0")
            connection.execute("""CREATE TABLE IF NOT EXISTS auth_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                provider TEXT NOT NULL, provider_subject TEXT NOT NULL,
                normalized_identifier TEXT, verified_at TEXT, created_at TEXT NOT NULL,
                last_used_at TEXT, UNIQUE(provider, provider_subject),
                FOREIGN KEY(user_id) REFERENCES users(id))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS otp_challenges (
                id TEXT PRIMARY KEY, user_id INTEGER, destination TEXT NOT NULL,
                purpose TEXT NOT NULL, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
                created_at TEXT NOT NULL, consumed_at TEXT, provider_request_id TEXT)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS persistent_sessions (
                id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, token_hash TEXT UNIQUE NOT NULL,
                tenant_id TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                revoked_at TEXT, last_used_at TEXT)""")
            session_columns = {row[1] for row in connection.execute("PRAGMA table_info(persistent_sessions)")}
            for name in ("user_agent", "ip_address", "auth_method"):
                if name not in session_columns: connection.execute(f"ALTER TABLE persistent_sessions ADD COLUMN {name} TEXT")
            connection.execute("""CREATE TABLE IF NOT EXISTS auth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
                user_id INTEGER, actor_id TEXT, tenant_id TEXT, correlation_id TEXT,
                method TEXT, outcome TEXT, reason TEXT, source_ip TEXT, created_at TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS auth_rate_limits (
                bucket_hash TEXT PRIMARY KEY, window_started TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0)""")
        self.rate_limit_backend = DatabaseRateLimitBackend(self.db)
        self.rate_limit_service = RateLimitService(self.rate_limit_backend)

    def register(self, username: str, email: str, password: str, role: str = "analyst", *, phone_number=None, phone_verified_at=None, tenant_id=None, actor_id=None, date_of_birth=None, email_verified_at=None, connection=None) -> User:
        if len(username.strip()) < 3 or "@" not in str(email) or len(password) < 10:
            raise ValueError("invalid_user_registration")
        normalized_role = str(role or "analyst").strip().lower()
        if normalized_role not in self.ROLES:
            raise ValueError("invalid_user_role")
        normalized_dob = validate_minimum_age(date_of_birth) if date_of_birth is not None else None
        now = datetime.now(timezone.utc).isoformat()
        def create_user(connection):
            if phone_number and connection.execute("SELECT 1 FROM users WHERE phone_number=?", (phone_number,)).fetchone(): raise ValueError("phone_already_registered")
            cursor = connection.execute(
                "INSERT INTO users(username,email,password_hash,role,created_at,phone_number,phone_verified_at,tenant_id,actor_id,date_of_birth,email_verified_at,session_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (username.strip(), email.strip().lower(), hash_password(password), normalized_role, now, phone_number, phone_verified_at, tenant_id, actor_id, normalized_dob, email_verified_at, 0),
            )
            user_id = cursor.lastrowid
            connection.execute(
                "INSERT OR IGNORE INTO auth_identities(user_id,provider,provider_subject,normalized_identifier,verified_at,created_at,last_used_at) VALUES(?,?,?,?,?,?,?)",
                (user_id, "password", str(user_id), email.strip().lower(), None, now, now),
            )
            return user_id
        if connection is None:
            with self.db.session() as owned_connection:
                user_id = create_user(owned_connection)
            return self.get_by_id(user_id)
        user_id = create_user(connection)
        return self._user(connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def authenticate(self, username: str, password: str) -> User | None:
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1", (username, username.strip().lower())).fetchone()
            if not row or not verify_password(row["password_hash"], password):
                return None
            now = datetime.now(timezone.utc).isoformat()
            connection.execute("UPDATE users SET last_login=? WHERE id=?", (now, row["id"]))
        return self.get_by_id(row["id"])

    def create_persistent_session(self, user, raw_token, tenant_id, session_id, expires, *, user_agent=None, ip_address=None, auth_method="password"):
        with self.db.session() as connection:
            connection.execute("INSERT INTO persistent_sessions(id,user_id,token_hash,tenant_id,created_at,expires_at,user_agent,ip_address,auth_method) VALUES(?,?,?,?,?,?,?,?,?)", (session_id, user.id, self._hash_token(raw_token), tenant_id, utcnow().isoformat(), expires, user_agent, ip_address, auth_method))

    def resolve_persistent_session(self, session_id, raw_token):
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM persistent_sessions WHERE id=? AND revoked_at IS NULL", (session_id,)).fetchone()
            if not row or datetime.fromisoformat(row["expires_at"]) <= utcnow() or not __import__('hmac').compare_digest(row["token_hash"], self._hash_token(raw_token)): return None
            connection.execute("UPDATE persistent_sessions SET last_used_at=? WHERE id=?", (utcnow().isoformat(), session_id))
        return self.get_by_id(row["user_id"])

    def revoke_persistent_session(self, session_id):
        with self.db.session() as connection: connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE id=?", (utcnow().isoformat(), session_id))

    def revoke_all_sessions(self, user_id, connection=None):
        def revoke(owned_connection):
            owned_connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (utcnow().isoformat(), user_id))
        if connection is None:
            with self.db.session() as owned_connection:
                revoke(owned_connection)
            return
        revoke(connection)

    def list_sessions(self, user_id):
        with self.db.session() as connection:
            return [dict(row) for row in connection.execute("SELECT id,user_id,tenant_id,created_at,expires_at,revoked_at,last_used_at,user_agent,auth_method FROM persistent_sessions WHERE user_id=? AND revoked_at IS NULL ORDER BY last_used_at DESC,created_at DESC", (user_id,)).fetchall()]

    def revoke_owned_session(self, user_id, session_id):
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE id=? AND user_id=? AND revoked_at IS NULL", (utcnow().isoformat(), session_id, user_id))
        return cursor.rowcount == 1

    def revoke_other_sessions(self, user_id, current_session_id):
        with self.db.session() as connection:
            cursor = connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE user_id=? AND id<>? AND revoked_at IS NULL", (utcnow().isoformat(), user_id, current_session_id or ""))
        return cursor.rowcount

    def reset_password(self, user_id, password, *, connection=None):
        if len(str(password or "")) < 10: raise ValueError("invalid_password")
        def reset(owned_connection):
            owned_connection.execute(
                "UPDATE users SET password_hash=?, session_version=COALESCE(session_version, 0)+1 WHERE id=?",
                (hash_password(password), user_id),
            )
            self.revoke_all_sessions(user_id, connection=owned_connection)
            self.audit_event("password_changed", user_id=user_id, outcome="success", method="password", connection=owned_connection)
        if connection is None:
            with self.db.session() as owned_connection:
                reset(owned_connection)
            return
        reset(connection)

    def add_identity(self, user_id, provider, subject, identifier=None):
        now = utcnow().isoformat()
        with self.db.session() as connection:
            connection.execute("INSERT INTO auth_identities(user_id,provider,provider_subject,normalized_identifier,verified_at,created_at,last_used_at) VALUES(?,?,?,?,?,?,?)", (user_id, provider, subject, identifier, now, now, now))

    def identity_user(self, provider, subject):
        with self.db.session() as connection:
            row = connection.execute("SELECT user_id FROM auth_identities WHERE provider=? AND provider_subject=?", (provider, subject)).fetchone()
        return self.get_by_id(row["user_id"]) if row else None

    def identities_for_user(self, user_id, connection=None):
        if connection is None:
            with self.db.session() as owned_connection:
                return [dict(row) for row in owned_connection.execute("SELECT * FROM auth_identities WHERE user_id=? ORDER BY provider", (user_id,)).fetchall()]
        return [dict(row) for row in connection.execute("SELECT * FROM auth_identities WHERE user_id=? ORDER BY provider", (user_id,)).fetchall()]

    def remove_identity(self, user_id, provider, subject=None):
        with self.db.session() as connection:
            if subject is None:
                connection.execute("DELETE FROM auth_identities WHERE user_id=? AND provider=?", (user_id, provider))
            else:
                connection.execute("DELETE FROM auth_identities WHERE user_id=? AND provider=? AND provider_subject=?", (user_id, provider, subject))

    def get_by_username(self, username, connection=None):
        normalized = str(username or "").strip()
        if not normalized:
            return None
        if connection is None:
            with self.db.session() as owned_connection:
                row = owned_connection.execute("SELECT * FROM users WHERE username=?", (normalized,)).fetchone()
        else:
            row = connection.execute("SELECT * FROM users WHERE username=?", (normalized,)).fetchone()
        return self._user(row) if row else None

    def get_by_email(self, email, connection=None, include_inactive=False):
        normalized = str(email or "").strip().lower()
        predicate = "email=?" if include_inactive else "email=? AND is_active=1"
        if connection is None:
            with self.db.session() as owned_connection:
                row = owned_connection.execute(f"SELECT * FROM users WHERE {predicate}", (normalized,)).fetchone()
        else:
            row = connection.execute(f"SELECT * FROM users WHERE {predicate}", (normalized,)).fetchone()
        return self._user(row) if row else None

    def deactivate_user(self, user_id: int, connection=None) -> bool:
        """Deactivate one user and revoke its persistent sessions."""
        def deactivate(owned_connection):
            cursor = owned_connection.execute("UPDATE users SET is_active=0 WHERE id=? AND is_active=1", (user_id,))
            owned_connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (utcnow().isoformat(), user_id))
            return cursor.rowcount == 1
        if connection is None:
            with self.db.session() as owned_connection:
                return deactivate(owned_connection)
        return deactivate(connection)

    def activate_user(self, user_id: int, connection=None) -> bool:
        """Activate one previously inactive user within the caller's transaction."""
        def activate(owned_connection):
            cursor = owned_connection.execute("UPDATE users SET is_active=1 WHERE id=? AND is_active=0", (user_id,))
            return cursor.rowcount == 1
        if connection is None:
            with self.db.session() as owned_connection:
                return activate(owned_connection)
        return activate(connection)

    def audit_event(self, event_type, *, user_id=None, actor_id=None, tenant_id=None,
                    correlation_id=None, method=None, outcome=None, reason=None, source_ip=None,
                    connection=None):
        def record(owned_connection):
            owned_connection.execute(
                "INSERT INTO auth_events(event_type,user_id,actor_id,tenant_id,correlation_id,method,outcome,reason,source_ip,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (event_type, user_id, actor_id, tenant_id, correlation_id, method, outcome, reason, source_ip, utcnow().isoformat()),
            )
        if connection is None:
            with self.db.session() as owned_connection:
                record(owned_connection)
            return
        record(connection)

    def rate_allow(self, bucket, *, limit, window_seconds, tenant_id=None, actor_id=None,
                   api_key_id=None, ip_address=None, endpoint="auth", operation=None,
                   cost_class="authentication"):
        policy = RateLimitPolicy(
            name=f"auth:{str(bucket).split('|', 1)[0]}",
            limit=limit,
            window_seconds=window_seconds,
            cost_class=cost_class,
        )
        decision = self.rate_limit_service.allow(
            RateLimitRequest(
                tenant_id=tenant_id,
                actor_id=actor_id,
                api_key_id=api_key_id,
                ip_address=ip_address,
                endpoint=endpoint,
                operation=operation or str(bucket).split("|", 1)[0],
                cost_class=cost_class,
            ),
            policy,
        )
        return decision.allowed

    def issue_otp(self, destination, purpose, *, user_id=None, secret="development-only-secret", provider_request_id=None):
        with self.db.session() as connection:
            recent = connection.execute("SELECT created_at FROM otp_challenges WHERE destination=? AND purpose=? ORDER BY created_at DESC LIMIT 1", (destination, purpose)).fetchone()
            if recent and datetime.fromisoformat(recent["created_at"]) + __import__('datetime').timedelta(seconds=OTP_COOLDOWN_SECONDS) > utcnow(): raise ValueError("otp_cooldown")
            code = generate_code(); challenge_id = __import__('uuid').uuid4().hex; now = utcnow().isoformat()
            connection.execute("UPDATE otp_challenges SET consumed_at=? WHERE destination=? AND purpose=? AND consumed_at IS NULL", (now, destination, purpose))
            connection.execute("INSERT INTO otp_challenges(id,user_id,destination,purpose,code_hash,expires_at,attempts,max_attempts,created_at,provider_request_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (challenge_id,user_id,destination,purpose,code_hash(code, secret),expires_at(),0, OTP_MAX_ATTEMPTS,now,provider_request_id))
        return challenge_id, code

    def verify_otp(self, challenge_id, code, *, secret="development-only-secret"):
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM otp_challenges WHERE id=?", (challenge_id,)).fetchone()
            if not row or row["consumed_at"] or datetime.fromisoformat(row["expires_at"]) <= utcnow() or row["attempts"] >= row["max_attempts"]: return None
            if not __import__('hmac').compare_digest(row["code_hash"], code_hash(str(code), secret)):
                connection.execute("UPDATE otp_challenges SET attempts=attempts+1 WHERE id=?", (challenge_id,)); return None
            connection.execute("UPDATE otp_challenges SET consumed_at=? WHERE id=?", (utcnow().isoformat(), challenge_id))
        return row["user_id"]

    @staticmethod
    def _hash_token(value):
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()

    def get_by_id(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return self._user(row) if row else None

    def session_user(self, user_id: int | None, session_version: int | None = None) -> User | None:
        """Return an active user only when the signed session epoch is current."""
        user = self.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        try:
            presented = 0 if session_version is None else int(session_version)
        except (TypeError, ValueError):
            return None
        return user if presented == user.session_version else None

    @staticmethod
    def _user(row: Any) -> User:
        return User(row["id"], row["username"], row["email"], row["password_hash"], row["role"], row["created_at"], row["last_login"], bool(row["is_active"]), row["phone_number"], row["phone_verified_at"], row["tenant_id"], row["actor_id"], row["date_of_birth"], row["email_verified_at"], int(row["session_version"] or 0))
