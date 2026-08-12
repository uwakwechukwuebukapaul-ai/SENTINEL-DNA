import os
import threading

import pytest

from sentinel_dna.platform.compliance import ComplianceService, RetentionPolicy
from sentinel_dna.platform.distributed import RedisCache, RedisRateLimitStore, RedisSessionStore
from sentinel_dna.platform.workers import BackgroundJob, InvestigationWorker, JobStore, INVESTIGATION_JOB
from sentinel_dna.saas.auth import AuthService
from sentinel_dna.saas.billing import BillingService
from sentinel_dna.saas.identity import Role

class Pipeline:
    def __init__(self, client): self.client=client; self.commands=[]
    def incr(self,key): self.commands.append(("incr",key)); return self
    def expire(self,key,seconds,nx=False): self.commands.append(("expire",key,seconds)); return self
    def execute(self):
        out=[]
        for command in self.commands:
            if command[0]=="incr": self.client.values[command[1]]=int(self.client.values.get(command[1],0))+1; out.append(self.client.values[command[1]])
            else: out.append(True)
        return out
class FakeRedis:
    def __init__(self): self.values={}
    def pipeline(self,transaction=True): return Pipeline(self)
    def set(self,key,value,ex=None): self.values[key]=value
    def get(self,key): return self.values.get(key)
    def delete(self,key): self.values.pop(key,None)

def test_redis_rate_limit_cache_and_session_are_tenant_namespaced():
    redis=FakeRedis(); limiter=RedisRateLimitStore("redis://unit",redis)
    assert limiter.allow("org-a:user",2,60) and limiter.allow("org-a:user",2,60) and not limiter.allow("org-a:user",2,60)
    cache=RedisCache("redis://unit",redis); cache.set("org-a","summary",{"value":1},60)
    assert cache.get("org-a","summary")=={"value":1} and cache.get("org-b","summary") is None
    sessions=RedisSessionStore("redis://unit",redis); sessions.put("digest","user-a",60); assert sessions.get("digest")=="user-a"; sessions.revoke("digest"); assert sessions.get("digest") is None

def test_authentication_mirrors_and_revokes_distributed_sessions(tmp_path):
    redis=FakeRedis(); sessions=RedisSessionStore("redis://unit",redis); auth=AuthService(str(tmp_path),session_store=sessions)
    auth.register("owner@example.com","correct horse battery staple","Owner")
    principal=auth.login("owner@example.com","correct horse battery staple")
    assert auth.authenticate_token(principal.token).user.email=="owner@example.com"
    auth.revoke_token(principal.token)
    assert sessions.get(__import__("hashlib").sha256(principal.token.encode()).hexdigest()) is None

def test_atomic_redis_limit_with_concurrent_calls():
    redis=FakeRedis(); limiter=RedisRateLimitStore("redis://unit",redis); results=[]
    threads=[threading.Thread(target=lambda: results.append(limiter.allow("same",3,60))) for _ in range(8)]
    [thread.start() for thread in threads]; [thread.join() for thread in threads]
    assert sum(results)==3

def test_async_job_status_and_tenant_isolation(tmp_path):
    auth=AuthService(str(tmp_path)); registered=auth.register("owner@example.com","correct horse battery staple","Owner","Acme")
    user,org=registered["user"],registered["organization"]
    BillingService(str(tmp_path)).create_subscription(org.organization_id,"plan-free","async-subscription-key")
    store=JobStore(tmp_path); job=store.enqueue(BackgroundJob(INVESTIGATION_JOB,org.organization_id,{"case_id":"async-1","alert":{"subject":"alert"}}),user.user_id)
    assert store.get(job.job_id,org.organization_id).status=="queued"
    with pytest.raises(PermissionError): store.get(job.job_id,"org-other")
    result=InvestigationWorker(tmp_path).run_once()
    assert result.status=="completed"

def test_compliance_export_and_tenant_activity_are_isolated(tmp_path):
    auth=AuthService(str(tmp_path)); a=auth.register("a@example.com","correct horse battery staple","A","A")["organization"]; b=auth.register("b@example.com","correct horse battery staple","B","B")["organization"]
    compliance=ComplianceService(tmp_path); compliance.archive_security_event(a.organization_id,"security_event",{"kind":"login_denied"})
    assert len(compliance.export_audit(a.organization_id))==1
    assert compliance.tenant_activity_report(b.organization_id)["event_count"]==0
    assert RetentionPolicy(audit_days=1).cutoff("audit")

@pytest.mark.skipif(not os.getenv("SENTINEL_DNA_TEST_POSTGRES_URL"), reason="requires managed PostgreSQL integration service")
def test_postgresql_integration_url_is_configured():
    from sentinel_dna.saas.database import SaaSDatabase
    assert SaaSDatabase("ignored", os.environ["SENTINEL_DNA_TEST_POSTGRES_URL"]).is_ready()
