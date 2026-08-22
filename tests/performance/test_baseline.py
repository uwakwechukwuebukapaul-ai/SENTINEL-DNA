from __future__ import annotations

import time

from services.intelligence.operations.operations_service import OperationsService
from services.intelligence.repository.report_repository import InvestigationReportRepository
from services.intelligence.workspace.evidence_graph import EvidenceGraphProjectionBuilder, InvestigationReportExportBuilder


def _timed(function):
    started = time.perf_counter()
    value = function()
    return round((time.perf_counter() - started) * 1000, 3), value


def test_production_read_path_baseline(canonical_authenticated_client, capsys):
    application = canonical_authenticated_client.application
    coordinator = application.container.require("investigation_coordinator")
    tenant_id = "tenant-a"

    view = {
        "investigation": {"case_id": "PERF-CASE", "id": "PERF-CASE", "status": "in_progress"},
        "evidence": [{"evidence_id": f"E-{index}", "type": "event", "source": "fixture"} for index in range(250)],
        "findings": [{"finding_id": f"F-{index}", "finding": "controlled finding", "evidence_refs": [f"E-{index}"]} for index in range(250)],
        "recommendations": [],
    }
    explainability = {"threat_intelligence": {"indicators": []}, "mitre": [], "timeline": []}
    graph_builder = EvidenceGraphProjectionBuilder()
    graph_ms, graph = _timed(lambda: graph_builder.build(view, explainability))
    report_ms, _ = _timed(lambda: InvestigationReportExportBuilder().build("PERF-CASE", view, explainability, graph))
    api_ms, _ = _timed(lambda: canonical_authenticated_client.get("/api/investigations/queue?page=1&page_size=25"))
    workspace_ms, _ = _timed(lambda: canonical_authenticated_client.get("/workspace/"))
    ops_ms, _ = _timed(lambda: OperationsService(coordinator).dashboard(tenant_id=tenant_id, actor_id="actor-a"))

    repository = InvestigationReportRepository(coordinator.report_repository.db)
    for index in range(120):
        repository.save({"case_id": f"PERF-{index:04d}", "status": "in_progress", "metadata": {"tenant_id": tenant_id}})
    pagination_ms, page = _timed(lambda: repository.page_for_tenant(tenant_id, page=4, page_size=25))

    assert len(graph["nodes"]) <= graph_builder.MAX_NODES
    assert page["total"] >= 120
    assert all(status == 200 for status in (canonical_authenticated_client.get("/api/investigations/queue").status_code, canonical_authenticated_client.get("/workspace/").status_code))
    print({"api_queue_ms": api_ms, "workspace_ms": workspace_ms, "graph_ms": graph_ms, "report_ms": report_ms, "operations_dashboard_ms": ops_ms, "large_tenant_pagination_ms": pagination_ms})
