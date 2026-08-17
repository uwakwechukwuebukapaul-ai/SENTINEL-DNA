"""
Sentinel DNA Investigation Orchestrator.

Canonical investigation workflow engine.

Architecture:

    InvestigationCoordinator
            |
            v
    InvestigationOrchestrator
            |
            +--> Investigator
            +--> Execution Engine
            +--> Reporter
            |
            v
      Investigation Result
            |
            +--> Memory Store
            +--> Workflow State

The orchestrator is intentionally kept as the canonical workflow
boundary. Runtime task execution remains infrastructure owned by
RuntimeTaskExecutor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from services.observability import ObservabilityService
import time

from services.intelligence.investigation.investigation_result import (
    InvestigationResult,
)


# ============================================================================
# Workflow State
# ============================================================================


@dataclass
class _WorkflowState:
    """
    Lightweight workflow state owned by the orchestrator.

    This deliberately mirrors the public behavior expected by the
    investigation orchestration tests without introducing another
    orchestration runtime.
    """

    _status: str = "created"

    def set_status(self, status: str) -> None:
        self._status = str(status)

    def status(self) -> str:
        return self._status


# ============================================================================
# Default Components
# ============================================================================


class _DefaultInvestigator:
    """
    Safe default investigator.

    Real investigation intelligence can be injected through the
    application container / InvestigationCoordinator.
    """

    def investigate(
        self,
        case_id: str,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "analysis": {
                "risk": "unknown",
            },
            "case_id": case_id,
            "artifacts": artifacts,
        }


class _DefaultExecutionEngine:
    """
    Safe default execution boundary.

    Actual runtime execution remains owned by RuntimeTaskExecutor.
    """

    def execute(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "completed",
            "action": "none",
        }


class _DefaultReporter:
    """
    Safe default report builder.
    """

    def build(
        self,
        case_id: str,
        orchestration_result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "status": orchestration_result.get(
                "status",
                "completed",
            ),
        }


# ============================================================================
# Compatibility Workflow
# ============================================================================


@dataclass
class InvestigationWorkflow:
    """
    Public compatibility representation of an investigation workflow.

    Existing consumers may import this symbol from the orchestration
    package. The object remains intentionally lightweight.
    """

    investigation_id: str
    case_id: str
    status: str = "created"
    artifacts: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "status": self.status,
            "artifacts": list(self.artifacts or []),
        }


# ============================================================================
# Investigation Orchestrator
# ============================================================================


class InvestigationOrchestrator:
    """
    Canonical Sentinel DNA investigation workflow orchestrator.

    Public contract:

        investigate(case_id, artifacts)

    Supported compatibility collaborators:

        investigator
        execution_engine
        reporter

    Runtime execution infrastructure should remain behind the
    execution boundary rather than creating another orchestrator.
    """

    PLAN_NAME = "Standard Security Investigation"

    def __init__(
        self,
        runtime: Any = None,
        registry: Any = None,
        investigator: Any = None,
        execution_engine: Any = None,
        reporter: Any = None,
        ai_runtime: Any = None,
        **kwargs: Any,
    ) -> None:
        self.runtime = runtime
        self.registry = registry

        self.investigator = (
            investigator
            if investigator is not None
            else _DefaultInvestigator()
        )

        self.execution_engine = (
            execution_engine
            if execution_engine is not None
            else _DefaultExecutionEngine()
        )

        self.reporter = (
            reporter
            if reporter is not None
            else _DefaultReporter()
        )

        self.ai_runtime = ai_runtime

        # Preserve historical orchestration state contract.
        self.state = _WorkflowState()

        # Preserve investigation memory contract.
        self.memory_store: dict[str, dict[str, Any]] = {}

        # Internal workflow registry.
        self._investigations: dict[
            str,
            dict[str, Any],
        ] = {}

    # ========================================================================
    # Investigation
    # ========================================================================

    def investigate(
        self,
        case_id: str,
        artifacts: Optional[list[Any]] = None,
        alert: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute the canonical investigation workflow.

        The method intentionally returns a dictionary for compatibility
        with the existing orchestration API tests and legacy callers.

        Workflow:

            created
              |
              v
            investigation
              |
              v
            execution
              |
              v
            report
              |
              v
           completed

        Any workflow exception produces a structured failed result.
        """

        started_at = time.perf_counter()
        observer = ObservabilityService()
        normalized_case_id = str(
            case_id or "UNKNOWN"
        )
        correlation_id = kwargs.get("correlation_id")

        normalized_artifacts = self._normalize_artifacts(
            artifacts
        )

        investigation_id = (
            f"INV-{normalized_case_id}"
        )

        alert_data = dict(
            alert or {}
        )

        alert_data["case_id"] = (
            normalized_case_id
        )

        alert_data.setdefault(
            "investigation_id",
            investigation_id,
        )

        self.state.set_status("created")

        try:
            # --------------------------------------------------------------
            # Investigation
            # --------------------------------------------------------------

            investigation = self.investigator.investigate(
                case_id=normalized_case_id,
                artifacts=normalized_artifacts,
            )

            if not isinstance(
                investigation,
                dict,
            ):
                investigation = {
                    "result": investigation,
                    "case_id": normalized_case_id,
                }

            investigation.setdefault(
                "case_id",
                normalized_case_id,
            )

            self.state.set_status(
                "investigating"
            )

            # --------------------------------------------------------------
            # Execution
            # --------------------------------------------------------------

            execution = self.execution_engine.execute(
                investigation=investigation,
            )

            if not isinstance(
                execution,
                dict,
            ):
                execution = {
                    "result": execution,
                }

            self.state.set_status(
                "executing"
            )

            ai_response = None
            context = kwargs.get("context")
            if self.ai_runtime is not None and context is not None:
                ai_response = self.ai_runtime.reason(context)

            # --------------------------------------------------------------
            # Intermediate orchestration result
            # --------------------------------------------------------------

            orchestration_result: dict[
                str,
                Any,
            ] = {
                "investigation_id": investigation_id,
                "case_id": normalized_case_id,
                "status": "completed",
                "plan_name": self.PLAN_NAME,
                "artifacts": normalized_artifacts,
                "alert": alert_data,
                "investigation": investigation,
                "execution": execution,
            }

            if ai_response is not None:
                orchestration_result.update({
                    "ai_reasoning": ai_response.content,
                    "ai_confidence": ai_response.confidence,
                    "ai_evidence_references": list(ai_response.evidence_references),
                    "ai_provider": ai_response.metadata.get("provider"),
                })

            # --------------------------------------------------------------
            # Report
            # --------------------------------------------------------------

            report = self.reporter.build(
                case_id=normalized_case_id,
                orchestration_result=(
                    orchestration_result
                ),
            )

            if not isinstance(
                report,
                dict,
            ):
                report = {
                    "result": report,
                    "case_id": normalized_case_id,
                }

            report.setdefault(
                "case_id",
                normalized_case_id,
            )

            report.setdefault(
                "status",
                "completed",
            )

            # --------------------------------------------------------------
            # Memory
            # --------------------------------------------------------------

            memory = self._create_memory(
                investigation_id=investigation_id,
                case_id=normalized_case_id,
                investigation=investigation,
                execution=execution,
                report=report,
            )

            # --------------------------------------------------------------
            # Final result
            # --------------------------------------------------------------

            self.state.set_status(
                "completed"
            )

            result: dict[str, Any] = {
                "success": True,
                "status": "completed",
                "message": (
                    "Investigation completed."
                ),
                "investigation_id": (
                    investigation_id
                ),
                "case_id": normalized_case_id,
                "plan_name": self.PLAN_NAME,
                "artifacts": normalized_artifacts,
                "alert": alert_data,
                "investigation": investigation,
                "execution": execution,
                "report": report,
                "memory": memory,
                "findings": [],
                "results": [],
                "errors": [],
                "intelligence": {
                    "investigation": investigation,
                    "execution": execution,
                    "report": report,
                },
                "ai_reasoning": orchestration_result.get("ai_reasoning"),
                "ai_confidence": orchestration_result.get("ai_confidence"),
                "ai_evidence_references": orchestration_result.get("ai_evidence_references", []),
                "ai_provider": orchestration_result.get("ai_provider"),
                "metadata": {
                    "orchestrator": (
                        "InvestigationOrchestrator"
                    ),
                    "state": self.state.status(),
                },
            }

            self._investigations[
                investigation_id
            ] = result

            observer.event(
                "AGENT_COMPLETED",
                case_id=normalized_case_id,
                status="completed",
                duration_ms=round((time.perf_counter()-started_at)*1000, 2),
                **({"correlation_id": correlation_id} if correlation_id else {}),
            )
            return result

        except Exception as exc:
            # --------------------------------------------------------------
            # Structured failure boundary
            # --------------------------------------------------------------

            self.state.set_status(
                "failed"
            )

            error_message = str(exc)

            memory = self._create_memory(
                investigation_id=investigation_id,
                case_id=normalized_case_id,
                investigation={},
                execution={},
                report={},
                confidence=0.0,
            )

            result = {
                "success": False,
                "status": "failed",
                "message": (
                    "Investigation workflow failed."
                ),
                "investigation_id": (
                    investigation_id
                ),
                "case_id": normalized_case_id,
                "plan_name": self.PLAN_NAME,
                "artifacts": normalized_artifacts,
                "alert": alert_data,
                "investigation": {},
                "execution": {},
                "report": {},
                "memory": memory,
                "findings": [],
                "results": [],
                "errors": [
                    error_message
                ],
                "intelligence": {},
                "metadata": {
                    "orchestrator": (
                        "InvestigationOrchestrator"
                    ),
                    "state": self.state.status(),
                },
            }

            self._investigations[
                investigation_id
            ] = result

            observer.event(
                "AGENT_FAILED",
                case_id=normalized_case_id,
                status="failed",
                duration_ms=round((time.perf_counter()-started_at)*1000, 2),
                errors=[str(exc)],
                **({"correlation_id": correlation_id} if correlation_id else {}),
            )
            return result

    # ========================================================================
    # Memory
    # ========================================================================

    def _create_memory(
        self,
        investigation_id: str,
        case_id: str,
        investigation: dict[str, Any],
        execution: dict[str, Any],
        report: dict[str, Any],
        confidence: float = 0.9,
    ) -> dict[str, Any]:
        """
        Create and persist investigation memory.

        Confidence defaults to 0.9 to preserve the established
        investigation-memory contract.
        """

        memory = {
            "investigation_id": (
                investigation_id
            ),
            "case_id": case_id,
            "confidence_history": [
                float(confidence)
            ],
            "investigation": investigation,
            "execution": execution,
            "report": report,
        }

        self.memory_store[
            case_id
        ] = memory

        return memory

    # ========================================================================
    # Helpers
    # ========================================================================

    @staticmethod
    def _normalize_artifacts(
        artifacts: Optional[list[Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[
            dict[str, Any]
        ] = []

        for artifact in artifacts or []:
            if isinstance(
                artifact,
                dict,
            ):
                normalized.append(
                    dict(artifact)
                )
            else:
                normalized.append(
                    {
                        "type": "unknown",
                        "value": artifact,
                    }
                )

        return normalized

    # ========================================================================
    # Compatibility / State
    # ========================================================================

    def get_investigation(
        self,
        investigation_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Return a previously created investigation.
        """

        return self._investigations.get(
            investigation_id
        )

    def get_memory(
        self,
        case_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Return investigation memory for a case.
        """

        return self.memory_store.get(
            case_id
        )

    def clear_memory(self) -> None:
        """
        Clear investigation memory and workflow state.
        """

        self.memory_store.clear()
        self._investigations.clear()

    def status(self) -> dict[str, Any]:
        """
        Return orchestrator health/status information.
        """

        return {
            "orchestrator": (
                "InvestigationOrchestrator"
            ),
            "plan_name": self.PLAN_NAME,
            "state": self.state.status(),
            "active_investigations": len(
                self._investigations
            ),
            "memory_entries": len(
                self.memory_store
            ),
        }


__all__ = [
    "InvestigationOrchestrator",
    "InvestigationWorkflow",
]
