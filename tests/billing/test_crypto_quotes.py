from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from services.billing.quotes import CryptoQuoteService, ExchangeRateSnapshot
from services.billing.exceptions import BillingError

class Rates:
    def __init__(self, age=0): self.age=age
    def get_rate(self, asset, fiat): return ExchangeRateSnapshot("snap-1",asset,fiat,Decimal("2000"),"approved",datetime.now(timezone.utc)-timedelta(seconds=self.age))

def test_quote_is_decimal_and_deterministically_rounded_down():
    quote=CryptoQuoteService(Rates()).create(tenant_id="tenant-a",plan_id="PRO",fiat_amount_minor=10001,fiat_currency="USD",asset="USDC",network="Ethereum",crypto_decimals=6,expiration_seconds=300)
    assert quote.crypto_amount == Decimal("0.050005") and quote.rounding_policy == "ROUND_DOWN"
    assert quote.quote_id and quote.tenant_id == "tenant-a"

def test_stale_rate_fails_closed():
    with pytest.raises(BillingError): CryptoQuoteService(Rates(61)).create(tenant_id="tenant-a",plan_id="PRO",fiat_amount_minor=100,fiat_currency="USD",asset="USDC",network="Ethereum",crypto_decimals=6,expiration_seconds=300)

def test_missing_tenant_fails_closed():
    with pytest.raises(BillingError): CryptoQuoteService(Rates()).create(tenant_id="",plan_id="PRO",fiat_amount_minor=100,fiat_currency="USD",asset="USDC",network="Ethereum",crypto_decimals=6,expiration_seconds=300)
