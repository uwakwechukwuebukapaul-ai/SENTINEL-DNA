"""SQLite-backed authentication service and secure auth lifecycle storage."""
from __future__ import annotations
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from database.connection import DatabaseConnection, database
from .models import User
from .security import hash_password, verify_password, token_hash
from .phone import normalize_phone
from .otp import generate_code, otp_digest, expiry, OTPDeliveryProvider
from .age import validate_minimum_age

class AuthService:
    ROLES = {"admin", "soc_manager", "analyst", "viewer"}
    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        with self.db.session() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'analyst', created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER NOT NULL DEFAULT 1, phone_number TEXT, phone_verified_at TEXT, tenant_id TEXT, actor_id TEXT)""")
            columns = {r[1] for r in c.execute("PRAGMA table_info(users)")}
            for name in ("phone_number", "phone_verified_at", "tenant_id", "actor_id", "date_of_birth"):
                if name not in columns: c.execute(f"ALTER TABLE users ADD COLUMN {name} TEXT")
            c.execute("""CREATE TABLE IF NOT EXISTS persistent_sessions (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, tenant_id TEXT, token_hash TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT, last_used_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS otp_verifications (id TEXT PRIMARY KEY, user_id INTEGER, pending_id TEXT, phone_number TEXT NOT NULL, purpose TEXT NOT NULL, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 5, created_at TEXT NOT NULL, consumed_at TEXT)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_otp_phone_created ON otp_verifications(phone_number, created_at)")
            c.execute("""CREATE TABLE IF NOT EXISTS pending_registrations (id TEXT PRIMARY KEY, username TEXT NOT NULL, email TEXT NOT NULL, password_hash TEXT NOT NULL, country TEXT NOT NULL, phone_number TEXT NOT NULL, date_of_birth TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)""")
            pending_columns = {r[1] for r in c.execute("PRAGMA table_info(pending_registrations)")}
            if "date_of_birth" not in pending_columns: c.execute("ALTER TABLE pending_registrations ADD COLUMN date_of_birth TEXT")

    def register(self, username, email, password, role="analyst", *, phone_number=None, phone_verified_at=None, tenant_id=None, actor_id=None, date_of_birth=None):
        if len(str(username).strip()) < 3 or "@" not in str(email) or len(password) < 10: raise ValueError("invalid_user_registration")
        normalized_dob = validate_minimum_age(date_of_birth) if date_of_birth is not None else None
        now = datetime.now(timezone.utc).isoformat()
        with self.db.session() as c:
            cur = c.execute("INSERT INTO users(username,email,password_hash,role,created_at,phone_number,phone_verified_at,tenant_id,actor_id,date_of_birth) VALUES(?,?,?,?,?,?,?,?,?,?)", (username.strip(), email.strip().lower(), hash_password(password), "analyst", now, phone_number, phone_verified_at, tenant_id, actor_id, normalized_dob))
            user_id = cur.lastrowid
        return self.get_by_id(user_id)

    def register_verified(self, username, email, password, country, phone, date_of_birth, *, canonical_authority):
        normalized = normalize_phone(country, phone); tenant_id, actor_id = f"tenant-{uuid4()}", f"actor-{uuid4()}"
        user = self.register(username, email, password, phone_number=normalized, phone_verified_at=datetime.now(timezone.utc).isoformat(), tenant_id=tenant_id, actor_id=actor_id, date_of_birth=date_of_birth)
        canonical_authority.tenants.create(f"{username.strip()}'s workspace", tenant_id=tenant_id)
        canonical_authority.identities.create(email, username.strip(), actor_id=actor_id); canonical_authority.memberships.add(tenant_id, actor_id, "analyst")
        return user

    def create_pending(self, username, email, password, country, phone, date_of_birth):
        normalized = normalize_phone(country, phone); normalized_dob = validate_minimum_age(date_of_birth); pending_id = str(uuid4()); now = datetime.now(timezone.utc)
        with self.db.session() as c:
            c.execute("INSERT INTO pending_registrations(id,username,email,password_hash,country,phone_number,date_of_birth,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?)", (pending_id, username.strip(), email.strip().lower(), hash_password(password), country, normalized, normalized_dob, now.isoformat(), (now + timedelta(minutes=15)).isoformat()))
        return pending_id, normalized

    def finalize_pending(self, pending_id, *, canonical_authority):
        with self.db.session() as c: row = c.execute("SELECT * FROM pending_registrations WHERE id=?", (pending_id,)).fetchone()
        if not row or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc): raise ValueError("registration_expired")
        tenant_id, actor_id = f"tenant-{uuid4()}", f"actor-{uuid4()}"; now = datetime.now(timezone.utc).isoformat()
        with self.db.session() as c:
            cur = c.execute("INSERT INTO users(username,email,password_hash,role,created_at,phone_number,phone_verified_at,tenant_id,actor_id,date_of_birth) VALUES(?,?,?,?,?,?,?,?,?,?)", (row["username"],row["email"],row["password_hash"],"analyst",now,row["phone_number"],now,tenant_id,actor_id,row["date_of_birth"])); user_id = cur.lastrowid
            c.execute("DELETE FROM pending_registrations WHERE id=?", (pending_id,))
        try:
            canonical_authority.tenants.create(f"{row['username']}'s workspace", tenant_id=tenant_id); canonical_authority.identities.create(row["email"], row["username"], actor_id=actor_id); canonical_authority.memberships.add(tenant_id, actor_id, "analyst")
        except Exception:
            with self.db.session() as c:
                c.execute("DELETE FROM users WHERE id=?", (user_id,))
                c.execute("DELETE FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (tenant_id, actor_id))
                c.execute("DELETE FROM canonical_identities WHERE actor_id=?", (actor_id,))
                c.execute("DELETE FROM canonical_tenants WHERE tenant_id=?", (tenant_id,))
            raise
        return self.get_by_id(user_id)

    def authenticate(self, username, password):
        with self.db.session() as c:
            value = str(username or "").strip(); row = c.execute("SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1", (value, value.lower())).fetchone()
            if not row or not verify_password(row["password_hash"], password): return None
            c.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), row["id"]))
        return self.get_by_id(row["id"])

    def issue_otp(self, phone_number, *, provider: OTPDeliveryProvider, purpose="phone_signup", user_id=None, pending_id=None):
        now = datetime.now(timezone.utc); cutoff = (now - timedelta(hours=1)).isoformat(); cooldown = (now - timedelta(seconds=60)).isoformat()
        with self.db.session() as c:
            recent = c.execute("SELECT created_at FROM otp_verifications WHERE phone_number=? AND created_at>? ORDER BY created_at DESC LIMIT 6", (phone_number, cutoff)).fetchall()
            if recent and recent[0][0] > cooldown: raise ValueError("otp_cooldown")
            if len(recent) >= 5: raise ValueError("otp_rate_limited")
            c.execute("UPDATE otp_verifications SET consumed_at=? WHERE phone_number=? AND purpose=? AND consumed_at IS NULL", (now.isoformat(), phone_number, purpose))
            secret, code, otp_id = secrets.token_urlsafe(16), generate_code(), str(uuid4())
            c.execute("INSERT INTO otp_verifications(id,user_id,pending_id,phone_number,purpose,code_hash,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?)", (otp_id,user_id,pending_id,phone_number,purpose,otp_digest(code, secret),expiry(),now.isoformat()))
        provider.send(phone_number, code, purpose=purpose); return otp_id, secret

    def verify_otp(self, phone_number, code, *, secret, purpose="phone_signup"):
        with self.db.session() as c:
            row = c.execute("SELECT * FROM otp_verifications WHERE phone_number=? AND purpose=? AND consumed_at IS NULL ORDER BY created_at DESC LIMIT 1", (phone_number,purpose)).fetchone()
            if not row: return False
            if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc) or row["attempts"] >= row["max_attempts"]:
                c.execute("UPDATE otp_verifications SET consumed_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(),row["id"])); return False
            if not secrets.compare_digest(row["code_hash"], otp_digest(str(code), secret)):
                c.execute("UPDATE otp_verifications SET attempts=attempts+1 WHERE id=?", (row["id"],)); return False
            c.execute("UPDATE otp_verifications SET consumed_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(),row["id"])); return True

    def create_persistent_session(self, user, days=30):
        raw, now = secrets.token_urlsafe(48), datetime.now(timezone.utc); expires, sid = now + timedelta(days=days), str(uuid4())
        with self.db.session() as c: c.execute("INSERT INTO persistent_sessions(id,user_id,tenant_id,token_hash,created_at,expires_at) VALUES(?,?,?,?,?,?)", (sid,user.id,user.tenant_id,token_hash(raw),now.isoformat(),expires.isoformat()))
        return f"{sid}.{raw}", expires

    def resolve_persistent_session(self, value):
        try: sid, raw = value.split(".", 1)
        except (AttributeError, ValueError): return None
        with self.db.session() as c:
            row = c.execute("SELECT * FROM persistent_sessions WHERE id=? AND revoked_at IS NULL", (sid,)).fetchone()
            if not row or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc) or not secrets.compare_digest(row["token_hash"], token_hash(raw)): return None
            c.execute("UPDATE persistent_sessions SET last_used_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(),sid))
        return self.get_by_id(row["user_id"])

    def revoke_persistent_sessions(self, user_id):
        with self.db.session() as c: c.execute("UPDATE persistent_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (datetime.now(timezone.utc).isoformat(), user_id))

    def get_by_id(self, user_id):
        if user_id is None: return None
        with self.db.session() as c: row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return self._user(row) if row else None

    @staticmethod
    def _user(row: Any):
        return User(row["id"], row["username"], row["email"], row["password_hash"], row["role"], row["created_at"], row["last_login"], bool(row["is_active"]), row["phone_number"], row["phone_verified_at"], row["tenant_id"], row["actor_id"], row["date_of_birth"])
