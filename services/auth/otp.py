"""Purpose-bound, hashed, single-use OTP challenges."""
from datetime import datetime, timedelta, timezone
import hashlib, hmac, secrets

OTP_TTL_SECONDS = 600
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60

def utcnow(): return datetime.now(timezone.utc)
def generate_code(): return f"{secrets.randbelow(1_000_000):06d}"
def code_hash(code: str, secret: str) -> str:
    return hmac.new(secret.encode(), code.encode(), hashlib.sha256).hexdigest()
def expires_at(): return (utcnow() + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
