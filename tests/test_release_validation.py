import logging
import os
from pathlib import Path

import pytest

from sentinel_dna.observability import JsonFormatter, ServiceMetrics
from sentinel_dna.platform.compliance import ComplianceService
from sentinel_dna.platform.workers import BackgroundJob, JobStore, INVESTIGATION_JOB
from sentinel_dna.saas.auth import AuthService, AuthenticationError
from sentinel_dna.workspace.web_app import create_app

def test_worker_crash_recovery_is_bounded_and_preserves_tenant(tmp_path):
    auth=AuthService(str(tmp_path)); registration=auth.register("a@example.com","correct horse battery staple","A","A")
    user,tenant=registration["user"],registration["organization"]
    store=JobStore(tmp_path); job=store.enqueue(BackgroundJob(INVESTIGATION_JOB,tenant.organization_id,{"case_id":"c","alert":{"subject":"a"}}),user.user_id)
    store.transition(job.job_id,tenant.organization_id,"queued","running")
    assert store.recover_running(max_attempts=1)==1
    recovered=store.get(job.job_id,tenant.organization_id)
    assert recovered.status=="queued" and recovered.attempts==1
    store.transition(job.job_id,tenant.organization_id,"queued","running")
    assert store.recover_running(max_attempts=1)==0

def test_authorization_penetration_attempts_and_token_lifecycle(tmp_path):
    client=create_app(str(tmp_path)).test_client()
    a=client.post("/auth/register",json={"email":"a@example.com","password":"correct horse battery staple","display_name":"A","organization_name":"A"})
    b=client.post("/auth/register",json={"email":"b@example.com","password":"correct horse battery staple","display_name":"B","organization_name":"B"})
    token=client.post("/auth/login",json={"email":"a@example.com","password":"correct horse battery staple"}).json["token"]
    assert client.get(f"/organizations/{b.json['organization']['organization_id']}",headers={"Authorization":f"Bearer {token}"}).status_code==403
    assert client.get("/auth/me",headers={"Authorization":"Bearer forged-token"}).status_code==401
    assert client.post("/auth/logout",headers={"Authorization":f"Bearer {token}"}).status_code==204
    assert client.get("/auth/me",headers={"Authorization":f"Bearer {token}"}).status_code==401

def test_audit_export_integrity_and_tenant_isolation(tmp_path):
    auth=AuthService(str(tmp_path)); a=auth.register("a@example.com","correct horse battery staple","A","A")["organization"]; b=auth.register("b@example.com","correct horse battery staple","B","B")["organization"]
    service=ComplianceService(tmp_path); service.archive_security_event(a.organization_id,"security_event",{"event":"denied"})
    exported=service.export_audit(a.organization_id)
    assert exported[0]["tenant_id"]==a.organization_id and service.export_audit(b.organization_id)==[]
    exported[0]["metadata"]["event"]="tampered"
    assert service.export_audit(a.organization_id)[0]["metadata"]["event"]=="denied"

def test_structured_logs_and_metrics_allowlist_sensitive_values():
    formatter=JsonFormatter(); record=logging.LogRecord("sentinel_dna",logging.INFO,"",0,"request",(),None)
    record.event_type="api_request"; record.password="secret"; record.token="bearer"
    rendered=formatter.format(record)
    assert '"event_type": "api_request"' in rendered and "secret" not in rendered and "bearer" not in rendered
    metrics=ServiceMetrics(); metrics.record_investigation("completed",12.5)
    assert "sentinel_dna_investigation_duration_milliseconds_total 12.5" in metrics.prometheus()

def test_helm_release_assets_include_security_controls():
    chart=Path("deploy/helm/sentinel-dna/templates")
    deployment=(chart / "deployment.yaml").read_text()
    assert (chart / "service.yaml").exists() and (chart / "networkpolicy.yaml").exists()
    assert "readOnlyRootFilesystem: true" in deployment and "secretRef" in deployment and "resources:" in deployment

@pytest.mark.skipif(not os.getenv("SENTINEL_DNA_TEST_REDIS_URL"), reason="requires managed Redis integration service")
def test_redis_integration_round_trip():
    from sentinel_dna.platform.distributed import RedisCache, RedisRateLimitStore
    url=os.environ["SENTINEL_DNA_TEST_REDIS_URL"]
    cache=RedisCache(url); cache.set("org-release","health",{"ok":True},30)
    assert cache.get("org-release","health")=={"ok":True}
    limiter=RedisRateLimitStore(url)
    assert limiter.allow("release-validation",1,30)
