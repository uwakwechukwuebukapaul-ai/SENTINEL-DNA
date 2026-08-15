from services.integration_runtime import *
from services.integration_runtime.service import IntegrationRuntimeService
class Adapter:
    def ingest(self, payload): return {"items": payload}
    def fail(self, payload): raise RuntimeError("offline")
def test_execution_and_tenant_isolation():
    service=IntegrationRuntimeService(); execution,result=service.execute("t1","c1",Adapter(),"ingest",[1]); assert execution.status==ExecutionStatus.SUCCESS and result["items"]==[1]; assert service.get_execution(execution.execution_id,"t2") is None
def test_receive_and_normalize():
    service=IntegrationRuntimeService(); event=service.receive("t1","c1",{"x":1}); assert event.tenant_id=="t1" and service.normalize("raw")["raw"]=="raw"
def test_failures_are_recorded():
    service=IntegrationRuntimeService(); execution,_=service.execute("t1","c1",Adapter(),"fail",None); assert execution.status in {ExecutionStatus.RETRYING,ExecutionStatus.FAILED} and execution.error_message
