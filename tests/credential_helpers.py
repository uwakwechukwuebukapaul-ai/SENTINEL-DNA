"""Per-run credentials for tests and synthetic demo flows."""

import secrets


def random_password() -> str:
    return secrets.token_urlsafe(32)


def random_secret() -> str:
    return secrets.token_urlsafe(48)


def random_token() -> str:
    return secrets.token_urlsafe(32)
