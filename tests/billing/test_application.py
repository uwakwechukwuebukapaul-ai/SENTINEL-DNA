from pathlib import Path
import pytest
from database.connection import DatabaseConnection
from database.canonical_authority import ensure_canonical_schema
from services.billing.application import BillingApplicationService, CheckoutRequest
from services.billing.repository import BillingRepository
from services.billing.service import BillingService
from services.billing.models import PaymentInitialization
from services.billing.exceptions import BillingError

class Context:
    def __init__(self,tenant_id): self.tenant_id=tenant_id
class Provider:
    callback_url="https://app.test/callback"
    def initialize_payment(self,**kw): return PaymentInitialization("",kw["reference"],"",kw["amount_minor"],kw["currency"],"https://pay.test/auth")
def setup(tmp_path):
    db=DatabaseConnection(Path(tmp_path)/"app.db")
    with db.session() as c:
        ensure_canonical_schema(c); c.execute("INSERT INTO canonical_tenants VALUES('a','A','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"); c.execute("INSERT INTO canonical_tenants VALUES('b','B','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
    repo=BillingRepository(db); billing=BillingService(Provider(),repository=repo); return BillingApplicationService(billing,repo),repo
def test_checkout_is_canonical_tenant_scoped_and_idempotent(tmp_path):
    app,_=setup(tmp_path); request=CheckoutRequest("PRO","user@example.com","key-1"); first=app.create_checkout_request(Context("a"),request); second=app.create_checkout_request(Context("a"),request); assert first==second and first.amount_minor==0
    with pytest.raises(BillingError): app.create_checkout_request(Context("missing"),request)
def test_cross_tenant_idempotency_isolated(tmp_path):
    app,_=setup(tmp_path); request=CheckoutRequest("PRO","user@example.com","same-key"); a=app.create_checkout_request(Context("a"),request); b=app.create_checkout_request(Context("b"),request); assert a.transaction_reference != b.transaction_reference
def test_status_is_tenant_scoped_and_requires_context(tmp_path):
    app,_=setup(tmp_path); app.create_checkout_request(Context("a"),CheckoutRequest("PRO","x@y.test","k")); status=app.get_billing_status(Context("a")); assert status.tenant_id=="a" and status.transaction_reference
    with pytest.raises(BillingError): app.get_billing_status(object())
def test_browser_cannot_supply_callback_or_price(tmp_path):
    app,_=setup(tmp_path)
    with pytest.raises(TypeError): app.create_checkout_request(Context("a"),CheckoutRequest("PRO","x@y.test","k"),"https://attacker.test")
