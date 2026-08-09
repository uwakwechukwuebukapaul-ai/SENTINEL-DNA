"""
Investigation Agent Tests.

Validates the Sentinel DNA autonomous investigation
agent foundation, execution state, findings, memory,
dependency injection, and edge-case handling.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.agent import (
    AgentExecutor,
    AgentState,
    InvestigationAgent,
    InvestigationMemory,
)


class FakeExecutor:
    """Deterministic executor used for dependency-injection tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def execute(
        self,
        state: AgentState,
        artifacts: list[dict[str, Any]],
    ) -> None:
        self.calls.append(
            {
                "case_id": state.case_id,
                "artifacts": artifacts,
            }
        )

        state.update_status("completed")

        state.current_step = "fake_execution"

        for artifact in artifacts:
            state.add_finding(
                {
                    "type": artifact.get(
                        "type",
                        "unknown",
                    ),
                    "value": artifact.get("value"),
                    "analysis": "fake analysis",
                }
            )


def test_agent_creation() -> None:
    """Agent should initialize with default dependencies."""

    agent = InvestigationAgent()

    assert agent is not None
    assert agent.executor is not None
    assert agent.memory is not None


def test_basic_investigation() -> None:
    """Agent should complete a basic investigation."""

    agent = InvestigationAgent()

    result = agent.investigate(
        {
            "case_id": "CASE-001",
            "indicators": [
                {
                    "type": "domain",
                    "value": "evil-domain.xyz",
                }
            ],
        }
    )

    assert result["case_id"] == "CASE-001"
    assert result["status"] == "completed"

    assert (
        result["investigation"]["confidence"]
        == 0.9
    )


def test_findings_created() -> None:
    """Investigation artifacts should produce findings."""

    agent = InvestigationAgent()

    result = agent.investigate(
        {
            "case_id": "CASE-002",
            "indicators": [
                {
                    "type": "file",
                    "value": "malware.exe",
                }
            ],
        }
    )

    findings = result["investigation"]["findings"]

    assert len(findings) == 1
    assert findings[0]["type"] == "file"
    assert findings[0]["value"] == "malware.exe"


def test_memory_tracking() -> None:
    """Completed investigations should be stored in memory."""

    agent = InvestigationAgent()

    agent.investigate(
        {
            "case_id": "CASE-003",
            "indicators": [],
        }
    )

    history = agent.memory.recall(
        "CASE-003"
    )

    assert len(history) == 1
    assert history[0]["case_id"] == "CASE-003"
    assert history[0]["status"] == "completed"


def test_empty_alert() -> None:
    """Agent should safely process an empty alert."""

    agent = InvestigationAgent()

    result = agent.investigate({})

    assert result["case_id"] == "UNKNOWN"
    assert result["status"] == "completed"

    assert (
        result["investigation"]["findings"]
        == []
    )


def test_agent_executor_directly() -> None:
    """Default executor should process artifacts."""

    executor = AgentExecutor()

    state = AgentState(
        case_id="CASE-004"
    )

    executor.execute(
        state,
        [
            {
                "type": "ip",
                "value": "10.10.10.10",
            }
        ],
    )

    assert state.status == "completed"
    assert (
        state.current_step
        == "artifact_analysis"
    )

    assert len(state.findings) == 1
    assert (
        state.findings[0]["value"]
        == "10.10.10.10"
    )


def test_agent_state_export() -> None:
    """Agent state should serialize cleanly."""

    state = AgentState(
        case_id="CASE-005"
    )

    state.update_status(
        "running"
    )

    state.current_step = (
        "artifact_analysis"
    )

    state.add_finding(
        {
            "type": "domain",
            "value": "evil.example",
        }
    )

    exported = state.export()

    assert exported["case_id"] == "CASE-005"
    assert exported["status"] == "running"
    assert (
        exported["current_step"]
        == "artifact_analysis"
    )

    assert len(
        exported["findings"]
    ) == 1


def test_investigation_memory_clear_case() -> None:
    """Memory should support clearing one case."""

    memory = InvestigationMemory()

    memory.remember(
        "CASE-006",
        {
            "status": "completed",
        },
    )

    memory.remember(
        "CASE-007",
        {
            "status": "completed",
        },
    )

    assert len(
        memory.recall("CASE-006")
    ) == 1

    memory.clear(
        "CASE-006"
    )

    assert (
        memory.recall("CASE-006")
        == []
    )

    assert len(
        memory.recall("CASE-007")
    ) == 1


def test_investigation_memory_clear_all() -> None:
    """Memory should support clearing all cases."""

    memory = InvestigationMemory()

    memory.remember(
        "CASE-008",
        {
            "status": "completed",
        },
    )

    memory.remember(
        "CASE-009",
        {
            "status": "completed",
        },
    )

    memory.clear()

    assert (
        memory.recall("CASE-008")
        == []
    )

    assert (
        memory.recall("CASE-009")
        == []
    )


def test_executor_dependency_injection() -> None:
    """Agent should support production-style dependency injection."""

    executor = FakeExecutor()

    memory = InvestigationMemory()

    agent = InvestigationAgent(
        executor=executor,
        memory=memory,
    )

    result = agent.investigate(
        {
            "case_id": "CASE-010",
            "indicators": [
                {
                    "type": "hash",
                    "value": "abc123",
                },
                {
                    "type": "domain",
                    "value": "malicious.example",
                },
            ],
        }
    )

    assert (
        result["case_id"]
        == "CASE-010"
    )

    assert (
        result["status"]
        == "completed"
    )

    assert len(
        executor.calls
    ) == 1

    assert (
        executor.calls[0]["case_id"]
        == "CASE-010"
    )

    assert (
        len(
            executor.calls[0]["artifacts"]
        )
        == 2
    )


def test_multiple_investigations_are_isolated() -> None:
    """Different cases should maintain independent memory."""

    agent = InvestigationAgent()

    agent.investigate(
        {
            "case_id": "CASE-011",
            "indicators": [
                {
                    "type": "domain",
                    "value": "one.example",
                }
            ],
        }
    )

    agent.investigate(
        {
            "case_id": "CASE-012",
            "indicators": [
                {
                    "type": "domain",
                    "value": "two.example",
                }
            ],
        }
    )

    case_one = agent.memory.recall(
        "CASE-011"
    )

    case_two = agent.memory.recall(
        "CASE-012"
    )

    assert len(case_one) == 1
    assert len(case_two) == 1

    assert (
        case_one[0]["case_id"]
        == "CASE-011"
    )

    assert (
        case_two[0]["case_id"]
        == "CASE-012"
    )


def test_timeline_is_generated() -> None:
    """Investigation execution should generate a timeline event."""

    agent = InvestigationAgent()

    result = agent.investigate(
        {
            "case_id": "CASE-013",
            "indicators": [],
        }
    )

    timeline = result["timeline"]

    assert len(timeline) == 1

    assert (
        timeline[0]["event"]
        == "Investigation execution completed"
    )

    assert "timestamp" in timeline[0]