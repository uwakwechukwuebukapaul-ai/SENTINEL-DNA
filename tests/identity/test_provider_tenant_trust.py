from pathlib import Path
import pytest
from database.connection import DatabaseConnection
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.provider_tenant_trust import ProviderTenantTrustError, ProviderTenantTrustService
from services.identity.request_context import CanonicalRequestContextService
from services.tenant.authorization import CanonicalTenantAuthorizationService

def setup(tmp_path):
    db=DatabaseConnection(Path(tmp_path)/"trust.db"); a=CanonicalAuthorityService(db); a.tenants.create("A","tenant-a"); a.identities.create("admin@x.com",actor_id="admin"); a.memberships.add("tenant-a","admin","admin"); c=CanonicalRequestContextService(a).resolve("tenant-a","admin"); return ProviderTenantTrustService(CanonicalTenantAuthorizationService(a),db),c
def test_trust_lifecycle_and_resolution(tmp_path):
    s,c=setup(tmp_path); t=s.create(c,"entra","https://issuer","external-a","tenant-a","admin"); assert s.resolve("entra","https://issuer","external-a").canonical_tenant_id=="tenant-a"; s.disable(c,t.trust_id)
    with pytest.raises(ProviderTenantTrustError): s.resolve("entra","https://issuer","external-a")
    s.reactivate(c,t.trust_id); s.revoke(c,t.trust_id)
    with pytest.raises(ProviderTenantTrustError): s.reactivate(c,t.trust_id)
def test_duplicate_and_unknown_tenant_fail(tmp_path):
    s,c=setup(tmp_path); s.create(c,"entra","https://issuer","external-a","tenant-a","admin")
    with pytest.raises(ProviderTenantTrustError): s.create(c,"entra","https://issuer","external-a","tenant-a","admin")
    with pytest.raises(ProviderTenantTrustError): s.create(c,"entra","http://issuer","external-b","missing","admin")
