"""Provider-neutral, single-use OTP primitives."""
from __future__ import annotations
import os, secrets
from datetime import datetime, timedelta, timezone
from typing import Protocol
from .security import token_hash

class OTPDeliveryProvider(Protocol):
    def send(self, phone_number: str, code: str, *, purpose: str) -> None: ...

class ConsoleOTPProvider:
    def send(self, phone_number: str, code: str, *, purpose: str) -> None: return None

class TestOTPProvider:
    __test__ = False

    def __init__(self): self.sent = []
    def send(self, phone_number: str, code: str, *, purpose: str) -> None: self.sent.append((phone_number, code, purpose))

def build_provider(*, testing=False, production=False):
    if testing: return TestOTPProvider()
    configured = os.getenv("SENTINEL_DNA_OTP_PROVIDER", "").strip().lower()
    if production and configured in {"", "console"}: raise RuntimeError("production_otp_provider_required")
    if configured in {"", "console"}: return ConsoleOTPProvider()
    raise RuntimeError("unsupported_otp_provider")

def generate_code(): return f"{secrets.randbelow(1000000):06d}"
def otp_digest(code, secret): return token_hash(f"{secret}:{code}")
def expiry(minutes=5): return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
