from services.intelligence.memory import InvestigationMemoryRepository, MemoryService


def inputs(case_id="C-1"):
    return ({"case_id": case_id, "evidence": [{"evidence_id": "E-1"}], "alert": {"type": "phishing"}},
            {"summary": "phishing", "confidence": .88, "findings": [], "mitre_techniques": ["T1566"]},
            {"case_id": case_id, "status": "completed", "success": True, "confidence": .88, "mitre": ["T1566"]})


def test_memory_storage():
    service = MemoryService(InvestigationMemoryRepository())
    record = service.store_investigation_memory(*inputs())
    assert record.synthetic_only and record.case_id == "C-1"


def test_memory_retrieval():
    service = MemoryService(InvestigationMemoryRepository()); service.store_investigation_memory(*inputs())
    assert len(service.retrieve_similar_investigations("security_investigation", "phishing")) == 1


def test_case_history():
    service = MemoryService(InvestigationMemoryRepository()); service.store_investigation_memory(*inputs())
    assert len(service.get_case_history("C-1")) == 1


def test_pattern_summary():
    service = MemoryService(InvestigationMemoryRepository()); service.store_investigation_memory(*inputs())
    assert service.summarize_patterns()["mitre_techniques"] == ["T1566"]


def test_duplicate_prevention():
    service = MemoryService(InvestigationMemoryRepository()); args = inputs(); service.store_investigation_memory(*args); service.store_investigation_memory(*args)
    assert len(service.get_case_history("C-1")) == 1


def test_orchestrator_memory_integration():
    service = MemoryService(InvestigationMemoryRepository()); record = service.store_investigation_memory(*inputs("C-2"))
    assert record.memory_id.startswith("MEM-")
