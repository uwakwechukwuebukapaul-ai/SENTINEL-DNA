import json
import pytest
from database.connection import DatabaseConnection
from database.canonical_authority import ensure_canonical_schema
from services.billing.repository import BillingRepository
from services.billing.events import NormalizedBillingEvent
from services.billing.transitions import BillingStateTransitionService
from services.billing.normalization import PaystackEventNormalizer
from services.billing.exceptions import BillingError, InvalidStateTransition

def setup(tmp_path):
    db=DatabaseConnection(tmp_path/"state.db")
    with db.session() as c:
        ensure_canonical_schema(c); c.execute("INSERT INTO canonical_tenants VALUES('a','A','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"); c.execute("INSERT INTO canonical_tenants VALUES('b','B','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
    repo=BillingRepository(db)
    with repo.transaction() as c:
        repo.create_transaction(c,"a","ref-a","paystack","PRO",100,"NGN"); repo.save_subscription(c,"a","paystack","PRO","PENDING")
    return repo
def event(**changes):
    values=dict(provider="paystack",provider_event_id="evt-1",event_type="charge.success",tenant_id="a",provider_transaction_reference="ref-a",transaction_status="SUCCESS",amount_minor=100,currency="NGN"); values.update(changes); return NormalizedBillingEvent(**values)
def test_transition_is_durable_and_duplicate_is_noop(tmp_path):
    service=BillingStateTransitionService(setup(tmp_path)); assert service.apply(event()).applied; assert service.apply(event()).duplicate
def test_cross_tenant_and_amount_mismatch_fail(tmp_path):
    service=BillingStateTransitionService(setup(tmp_path))
    with pytest.raises(BillingError): service.apply(event(tenant_id="b"))
    with pytest.raises(BillingError): service.apply(event(provider_event_id="evt-2",amount_minor=999))
def test_illegal_transition_rolls_back_and_can_retry(tmp_path):
    service=BillingStateTransitionService(setup(tmp_path)); service.apply(event());
    with pytest.raises(InvalidStateTransition): service.apply(event(provider_event_id="evt-2",transaction_status="PENDING"))
    with service.repository.transaction() as c: assert not service.repository.event_exists(c,"evt-2")
def test_normalizer_requires_trusted_tenant_and_does_not_use_provider_metadata():
    payload={"id":"evt","event":"charge.success","data":{"reference":"ref","status":"success","amount":100,"currency":"NGN","metadata":{"sentinel_tenant_id":"attacker"}}}
    normalized=PaystackEventNormalizer().normalize(payload,"canonical-a"); assert normalized.tenant_id=="canonical-a"
    with pytest.raises(BillingError): PaystackEventNormalizer().normalize(payload,None)
