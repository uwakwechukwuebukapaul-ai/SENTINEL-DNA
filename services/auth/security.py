"""Password and authentication security helpers."""

from werkzeug.security import check_password_hash, generate_password_hash
import secrets
import hashlib


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def csrf_token() -> str:
    return secrets.token_urlsafe(32)

def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
