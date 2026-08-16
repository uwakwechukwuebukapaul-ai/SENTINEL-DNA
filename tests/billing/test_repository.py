import pytest
from pathlib import Path
from database.connection import DatabaseConnection
from database.canonical_authority import ensure_canonical_schema
from services.billing.repository import BillingRepository
from services.billing.exceptions import BillingError

def setup_db(tmp_path):
    db=DatabaseConnection(Path(tmp_path)/"billing.db")
    with db.session() as c:
        ensure_canonical_schema(c); c.execute("INSERT INTO canonical_tenants VALUES('tenant-a','A','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
    return db
def test_repository_persists_and_is_tenant_scoped(tmp_path):
    repo=BillingRepository(setup_db(tmp_path))
    with repo.transaction() as c:
        repo.create_transaction(c,"tenant-a","ref-1","paystack","PRO",100,"NGN")
        repo.save_subscription(c,"tenant-a","paystack","PRO","ACTIVE")
        assert repo.record_event(c,"evt-1","paystack","charge.success","ref-1")
        assert not repo.record_event(c,"evt-1","paystack","charge.success","ref-1")
    with repo.transaction() as c: assert repo.get_transaction(c,"ref-1")["tenant_id"]=="tenant-a" and repo.get_subscription(c,"tenant-a")["status"]=="ACTIVE"
def test_missing_or_inactive_tenant_fails_closed(tmp_path):
    repo=BillingRepository(setup_db(tmp_path))
    with pytest.raises(BillingError):
        with repo.transaction() as c: repo.create_transaction(c,"missing","ref","paystack","PRO",1,"NGN")
    with repo.transaction() as c: c.execute("UPDATE canonical_tenants SET status='inactive' WHERE tenant_id='tenant-a'")
    with pytest.raises(BillingError):
        with repo.transaction() as c: repo.create_transaction(c,"tenant-a","ref-2","paystack","PRO",1,"NGN")
def test_transaction_rolls_back(tmp_path):
    repo=BillingRepository(setup_db(tmp_path))
    with pytest.raises(RuntimeError):
        with repo.transaction() as c:
            repo.create_transaction(c,"tenant-a","rollback","paystack","PRO",1,"NGN"); raise RuntimeError("stop")
    with repo.transaction() as c: assert repo.get_transaction(c,"rollback") is None
