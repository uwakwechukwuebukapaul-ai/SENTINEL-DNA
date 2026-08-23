from database.connection import DatabaseConnection
from services.intelligence.orchestration.investigation_coordinator import InvestigationCoordinator
from services.intelligence.repository.execution_repository import ExecutionRepository
from services.intelligence.runtime.runtime_task_executor import RuntimeTaskExecutor
from services.intelligence.agents.agent_registry import AgentRegistry
from services.intelligence.agents.bootstrap import bootstrap_agents
from services.intelligence.agents.runtime_adapter import AgentRuntimeAdapter


def test_powershell_alert_produces_evidence_backed_investigation_projection(tmp_path):
    runtime = RuntimeTaskExecutor()
    registry = AgentRegistry()
    bootstrap_agents(registry, runtime_adapter=AgentRuntimeAdapter(runtime))
    coordinator = InvestigationCoordinator(
        registry=registry,
        runtime=runtime,
        execution_repository=ExecutionRepository(DatabaseConnection(tmp_path / "execution.sqlite")),
    )

    result = coordinator.investigate(
        case_id="CASE-POWERSHELL-001",
        alert={
            "source": "endpoint",
            "title": "Suspicious PowerShell execution",
            "severity": "high",
            "user": "alice",
            "host": "WKST-17",
        },
        artifacts=[
            {
                "type": "process",
                "source": "endpoint_sensor",
                "host": "WKST-17",
                "user": "alice",
                "command_line": "powershell.exe -NoProfile -EncodedCommand ZQB2AGkAbAA=",
            },
            {
                "type": "ioc",
                "source": "endpoint_sensor",
                "value": "cdn-update.example.test",
            },
        ],
        iocs=[{"type": "domain", "value": "cdn-update.example.test"}],
        tenant_id="tenant-investigator",
        actor_id="analyst-1",
        correlation_id="corr-powershell-001",
    )

    assert result.success is True
    projection = result.projection.to_dict()
    assert projection["version"] == "investigation-projection-v1"
    assert projection["execution_status"]["status"] == "completed"
    assert projection["evidence"]
    evidence_ids = {item["evidence_id"] for item in projection["evidence"]}
    assert all(item["evidence_id"] for item in projection["evidence"])
    assert any("T1059.001" == item["technique_id"] for item in projection["attack_mapping"])
    assert all(set(item["supporting_evidence_ids"]).issubset(evidence_ids) for item in projection["attack_mapping"])
    assert projection["reasoning"]
    assert projection["confidence"]["score"] > 0
    assert projection["decision"]["confidence"] is not None
    assert projection["analyst_actions"]
    assert result.intelligence["report"]["case_id"] == "CASE-POWERSHELL-001"
    durable = ExecutionRepository(DatabaseConnection(tmp_path / "execution.sqlite")).get(
        result.execution_id,
        "tenant-investigator",
    )
    assert durable["status"] == "COMPLETED"
    assert durable["correlation_id"] == "corr-powershell-001"
    assert [item["to"] for item in durable["state_history"]] == ["QUEUED", "RUNNING", "COMPLETED"]
    assert durable["task_states"]
    assert all(item["state"] == "SUCCESS" for item in durable["task_states"])


def test_missing_runtime_capability_persists_terminal_failure(tmp_path):
    runtime = RuntimeTaskExecutor()
    coordinator = InvestigationCoordinator(
        runtime=runtime,
        execution_repository=ExecutionRepository(DatabaseConnection(tmp_path / "execution.sqlite")),
    )
    coordinator._get_plan_capabilities = lambda _plan: ["capability-not-registered"]

    result = coordinator.investigate(
        case_id="CASE-RUNTIME-MISSING",
        alert={"title": "Missing runtime capability"},
        tenant_id="tenant-investigator",
        actor_id="analyst-1",
        correlation_id="corr-runtime-missing",
    )

    assert result.success is False
    durable = ExecutionRepository(DatabaseConnection(tmp_path / "execution.sqlite")).get(
        result.execution_id,
        "tenant-investigator",
    )
    assert durable["status"] == "FAILED"
    assert [item["to"] for item in durable["state_history"]] == ["QUEUED", "FAILED"]
    assert durable["failures"][0]["error_code"] == "runtime_capability_missing"


def test_runtime_failure_is_not_reported_as_success():
    runtime = RuntimeTaskExecutor()
    runtime.register("broken", lambda _payload: (_ for _ in ()).throw(RuntimeError("secret detail")))
    from services.intelligence.runtime.task import Task

    task = Task("broken", {"case_id": "CASE-FAILURE"})
    failure = runtime.execute(task)

    assert failure["status"] == "failed"
    assert failure["error_code"] == "handler_exception"
    assert failure["error"] == "Capability handler failed"
    assert failure["metadata"]["exception_type"] == "RuntimeError"
    assert task.execution_status == "failed"
