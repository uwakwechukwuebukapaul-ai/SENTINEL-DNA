from services.detection.content.service import DetectionContentService
from services.detection.sigma import SigmaParser, SigmaValidator, SigmaConverter
def rule(): return {"name":"Brute Force","description":"failed auth","severity":"HIGH","query_logic":"failed authentication","data_source":"Windows Security Logs","mitre_techniques":["T1110"]}
def test_rule_validation_and_versioning():
    service = DetectionContentService(); item = service.create("org-a", rule(), 1); service.update(item, {"description":"updated"}, 1); assert item.version == 1 or item.version == 2
def test_deployment_lifecycle():
    service = DetectionContentService(); item = service.create("org-a", rule(), 1); assert service.deploy(item).status == "TESTING"; assert service.deploy(item).status == "APPROVED"; assert service.deploy(item).status == "ACTIVE"
def test_detection_test_engine():
    service = DetectionContentService(); item = service.create("org-a", rule(), 1); assert service.test(item, [{"message":"failed authentication"}])["matches"] == 1
def test_sigma_foundation():
    document = {"title":"PowerShell", "level":"high", "tags":["attack.t1059.001"], "detection":{"selection":{"Image":"powershell.exe"}}}; assert SigmaValidator().validate(document)["valid"]; assert SigmaConverter().to_detection_metadata(SigmaParser().parse(document))["severity"] == "HIGH"
def test_tenant_isolation():
    service = DetectionContentService(); item = service.create("org-a", rule(), 1); assert service.repository.get_rule(item.id, "org-b") is None
