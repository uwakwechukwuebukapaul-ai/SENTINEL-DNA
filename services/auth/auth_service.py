"""SQLite-backed authentication service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.connection import DatabaseConnection, database
from .models import User
from .security import hash_password, verify_password


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

    def register(self, username: str, email: str, password: str, role: str = "analyst") -> User:
        role = str(role or "analyst").strip().lower()
        if role not in self.ROLES or len(username.strip()) < 3 or len(password) < 10:
            raise ValueError("invalid_user_registration")
        now = datetime.now(timezone.utc).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute(
                "INSERT INTO users(username,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                (username.strip(), email.strip().lower(), hash_password(password), role, now),
            )
            user_id = cursor.lastrowid
        return self.get_by_id(user_id)

    def authenticate(self, username: str, password: str) -> User | None:
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,)).fetchone()
            if not row or not verify_password(row["password_hash"], password):
                return None
            now = datetime.now(timezone.utc).isoformat()
            connection.execute("UPDATE users SET last_login=? WHERE id=?", (now, row["id"]))
        return self.get_by_id(row["id"])

    def get_by_id(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return self._user(row) if row else None

    @staticmethod
    def _user(row: Any) -> User:
        return User(row["id"], row["username"], row["email"], row["password_hash"], row["role"], row["created_at"], row["last_login"], bool(row["is_active"]))
