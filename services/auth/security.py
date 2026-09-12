"""Password and authentication security helpers."""

from werkzeug.security import check_password_hash, generate_password_hash
import secrets


def password_strength_score(password: str) -> int:
    """Return a small deterministic server-side password strength score."""
    value = str(password or "")
    return sum(
        (
            len(value) >= 10,
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
    )


def validate_password(password: str) -> None:
    """Enforce the product's minimum password policy server-side."""
    if password_strength_score(password) < 4:
        raise ValueError("invalid_password")


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def csrf_token() -> str:
    return secrets.token_urlsafe(32)
