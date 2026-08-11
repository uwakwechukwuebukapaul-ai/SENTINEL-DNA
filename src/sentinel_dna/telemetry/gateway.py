from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.telemetry.adapters import TelemetryAdapter
from sentinel_dna.telemetry.models import (
    SecurityAlert,
    TelemetryValidationError,
)


@dataclass(frozen=True)
class TelemetryIngestionResult:
    """
    Stable result contract for telemetry ingestion.

    The gateway owns normalization and handoff. Investigation execution
    remains owned by InvestigationCoordinator.
    """

    success: bool
    adapter: str
    alert: SecurityAlert | None = None
    investigation: Any | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-serializable representation of the ingestion result.
        """

        investigation = None

        if self.investigation is not None:
            to_dict = getattr(self.investigation, "to_dict", None)

            if callable(to_dict):
                investigation = to_dict()
            else:
                investigation = self.investigation

        return {
            "success": self.success,
            "adapter": self.adapter,
            "alert": (
                self.alert.to_dict()
                if self.alert is not None
                else None
            ),
            "investigation": investigation,
            "errors": list(self.errors),
        }


class TelemetryIngestionGateway:
    """
    Enterprise telemetry ingestion boundary.

    Responsibilities:
    - validate and select a registered telemetry adapter
    - normalize vendor telemetry into SecurityAlert
    - validate the adapter output contract
    - optionally execute the canonical investigation flow
    - return a stable, serializable ingestion result

    Responsibilities intentionally excluded:
    - investigation planning
    - investigation task execution
    - threat intelligence logic
    - risk calculation
    - response automation

    Those responsibilities remain inside the canonical investigation
    architecture.
    """

    def __init__(
        self,
        adapters: dict[str, TelemetryAdapter],
        investigation_coordinator: InvestigationCoordinator | None = None,
    ) -> None:
        if not adapters:
            raise ValueError("at least one telemetry adapter is required")

        normalized_adapters: dict[str, TelemetryAdapter] = {}

        for name, adapter in adapters.items():
            normalized_name = self._normalize_registered_adapter_name(name)

            if not isinstance(adapter, TelemetryAdapter):
                raise TypeError(
                    f"adapter '{name}' must implement TelemetryAdapter"
                )

            if normalized_name in normalized_adapters:
                raise ValueError(
                    f"duplicate adapter name after normalization: "
                    f"{normalized_name}"
                )

            normalized_adapters[normalized_name] = adapter

        self._adapters = normalized_adapters
        self._investigation_coordinator = investigation_coordinator

    @property
    def adapters(self) -> tuple[str, ...]:
        """
        Return registered adapter names in deterministic order.
        """

        return tuple(sorted(self._adapters))

    def ingest(
        self,
        raw_event: Any,
        *,
        adapter: str,
        case_id: str | None = None,
        investigate: bool = False,
    ) -> TelemetryIngestionResult:
        """
        Normalize a raw telemetry event.

        If investigate=True, case_id is required and the normalized alert
        is passed to InvestigationCoordinator.
        """

        try:
            adapter_name = self._normalize_adapter_name(adapter)
        except ValueError as exc:
            return TelemetryIngestionResult(
                success=False,
                adapter=self._safe_adapter_name(adapter),
                errors=[
                    self._error(
                        stage="adapter_selection",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                ],
            )

        selected_adapter = self._adapters.get(adapter_name)

        if selected_adapter is None:
            return TelemetryIngestionResult(
                success=False,
                adapter=adapter_name,
                errors=[
                    self._error(
                        stage="adapter_selection",
                        error_type="UnsupportedAdapterError",
                        message=(
                            f"unsupported telemetry adapter: "
                            f"{adapter_name}"
                        ),
                    )
                ],
            )

        normalized_case_id: str | None = None

        if investigate:
            try:
                normalized_case_id = self._normalize_case_id(case_id)
            except ValueError as exc:
                return TelemetryIngestionResult(
                    success=False,
                    adapter=adapter_name,
                    errors=[
                        self._error(
                            stage="investigation_validation",
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    ],
                )

        try:
            alert = selected_adapter.normalize(raw_event)
        except TelemetryValidationError as exc:
            return TelemetryIngestionResult(
                success=False,
                adapter=adapter_name,
                errors=[
                    self._error(
                        stage="normalization",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                ],
            )
        except Exception as exc:
            return TelemetryIngestionResult(
                success=False,
                adapter=adapter_name,
                errors=[
                    self._error(
                        stage="normalization",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                ],
            )

        if not isinstance(alert, SecurityAlert):
            return TelemetryIngestionResult(
                success=False,
                adapter=adapter_name,
                errors=[
                    self._error(
                        stage="normalization_contract",
                        error_type="TelemetryAdapterContractError",
                        message=(
                            "telemetry adapter must return "
                            "SecurityAlert"
                        ),
                    )
                ],
            )

        investigation_result = None

        if investigate:
            if self._investigation_coordinator is None:
                return TelemetryIngestionResult(
                    success=False,
                    adapter=adapter_name,
                    alert=alert,
                    errors=[
                        self._error(
                            stage="investigation_handoff",
                            error_type="RuntimeError",
                            message=(
                                "investigation coordinator is not "
                                "configured"
                            ),
                        )
                    ],
                )

            try:
                investigation_result = (
                    self._investigation_coordinator.investigate(
                        normalized_case_id,
                        alert.to_investigation_alert(),
                    )
                )
            except Exception as exc:
                return TelemetryIngestionResult(
                    success=False,
                    adapter=adapter_name,
                    alert=alert,
                    errors=[
                        self._error(
                            stage="investigation_handoff",
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    ],
                )

        return TelemetryIngestionResult(
            success=True,
            adapter=adapter_name,
            alert=alert,
            investigation=investigation_result,
            errors=[],
        )

    @staticmethod
    def _normalize_adapter_name(adapter: str) -> str:
        """
        Normalize an adapter name supplied at ingestion time.
        """

        if not isinstance(adapter, str) or not adapter.strip():
            raise ValueError("adapter must be a non-empty string")

        return adapter.strip().lower()

    @classmethod
    def _normalize_registered_adapter_name(
        cls,
        adapter: str,
    ) -> str:
        """
        Normalize an adapter name during gateway construction.
        """

        if not isinstance(adapter, str) or not adapter.strip():
            raise ValueError(
                "adapter names must be non-empty strings"
            )

        return adapter.strip().lower()

    @staticmethod
    def _normalize_case_id(case_id: str | None) -> str:
        """
        Validate and canonicalize an investigation case ID.
        """

        if not isinstance(case_id, str):
            raise ValueError(
                "case_id is required when investigate=True"
            )

        normalized = case_id.strip()

        if not normalized:
            raise ValueError("case_id cannot be empty")

        return normalized

    @staticmethod
    def _safe_adapter_name(adapter: Any) -> str:
        """
        Produce a deterministic adapter value for an error result.

        This prevents invalid objects from breaking the structured result
        contract.
        """

        if isinstance(adapter, str):
            return adapter.strip().lower()

        return ""

    @staticmethod
    def _error(
        *,
        stage: str,
        error_type: str,
        message: str,
    ) -> dict[str, str]:
        """
        Construct the stable structured gateway error contract.
        """

        return {
            "stage": stage,
            "type": error_type,
            "message": message,
        }