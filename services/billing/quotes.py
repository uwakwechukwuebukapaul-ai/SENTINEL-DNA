"""Provider-neutral immutable crypto quote boundary."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Protocol
import uuid

from .exceptions import BillingError

class ExchangeRateProvider(Protocol):
    def get_rate(self, asset: str, fiat_currency: str): ...

@dataclass(frozen=True)
class ExchangeRateSnapshot:
    snapshot_id: str; asset: str; fiat_currency: str; rate: Decimal; source: str; observed_at: datetime

@dataclass(frozen=True)
class CryptoQuote:
    quote_id: str; tenant_id: str; plan_id: str; fiat_amount_minor: int; fiat_currency: str; asset: str; network: str; rate: Decimal; crypto_amount: Decimal; rate_source: str; rate_timestamp: datetime; expires_at: datetime; rounding_policy: str

class CryptoQuoteService:
    def __init__(self, rate_provider, *, max_rate_age_seconds=60): self.rate_provider, self.max_rate_age_seconds = rate_provider, max_rate_age_seconds
    def create(self, *, tenant_id, plan_id, fiat_amount_minor, fiat_currency, asset, network, crypto_decimals, expiration_seconds):
        if not tenant_id or fiat_amount_minor < 0 or crypto_decimals < 0 or expiration_seconds <= 0: raise BillingError("crypto_quote_invalid")
        snapshot = self.rate_provider.get_rate(asset, fiat_currency)
        now = datetime.now(timezone.utc)
        if not isinstance(snapshot, ExchangeRateSnapshot) or snapshot.rate <= 0 or not snapshot.source or (now - snapshot.observed_at).total_seconds() > self.max_rate_age_seconds: raise BillingError("crypto_rate_stale_or_unavailable")
        amount = (Decimal(fiat_amount_minor) / Decimal(100) / snapshot.rate).quantize(Decimal(1).scaleb(-crypto_decimals), rounding=ROUND_DOWN)
        if amount <= 0: raise BillingError("crypto_quote_amount_invalid")
        return CryptoQuote(str(uuid.uuid4()), tenant_id, plan_id, int(fiat_amount_minor), fiat_currency, asset, network, snapshot.rate, amount, snapshot.source, snapshot.observed_at, now.replace(microsecond=0) + __import__('datetime').timedelta(seconds=expiration_seconds), "ROUND_DOWN")
