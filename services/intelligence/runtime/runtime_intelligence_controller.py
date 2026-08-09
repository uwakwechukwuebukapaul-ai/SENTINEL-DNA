"""
Runtime Intelligence Controller

Coordinates runtime intelligence capability registration,
request normalization, execution, lifecycle and status
reporting.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class InvestigationContext:
    """
    Normalized runtime intelligence context.

    The runtime accepts lightweight identifiers such as
    ``INC-001`` but capability handlers receive a stable
    context object.
    """

    investigation_id: Optional[str] = None

    case_id: Optional[str] = None

    capability: Optional[str] = None

    payload: Any = None

    metadata: dict = field(
        default_factory=dict
    )


class RuntimeIntelligenceAPI:
    """
    Lightweight capability registry used by the
    Runtime Intelligence Controller.
    """

    def __init__(
        self,
    ):
        self.handlers = {}

        self.requests = 0

        self.executions = 0

        self.failures = 0

    # =========================================================
    # REGISTRATION
    # =========================================================

    def register(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        """
        Register a runtime intelligence capability.
        """

        if not capability:
            return False

        if not callable(handler):
            return False

        self.handlers[capability] = handler

        return True

    def unregister(
        self,
        capability: str,
    ) -> bool:
        """
        Remove a registered capability.
        """

        if capability not in self.handlers:
            return False

        del self.handlers[capability]

        return True

    # =========================================================
    # LOOKUP
    # =========================================================

    def available(
        self,
        capability: str,
    ) -> bool:
        return capability in self.handlers

    def exists(
        self,
        capability: str,
    ) -> bool:
        return self.available(
            capability
        )

    # =========================================================
    # EXECUTION
    # =========================================================

    def execute(
        self,
        capability: str,
        context: InvestigationContext,
    ):
        """
        Execute a registered capability.

        Returns the handler's native result.
        """

        self.requests += 1

        handler = self.handlers.get(
            capability
        )

        if handler is None:
            self.failures += 1

            return None

        try:

            result = handler(
                context
            )

            self.executions += 1

            return result

        except Exception:

            self.failures += 1

            raise

    # =========================================================
    # STATUS
    # =========================================================

    def status(
        self,
    ):
        return {
            "healthy": True,

            "capabilities":
                len(
                    self.handlers
                ),

            "requests":
                self.requests,

            "executions":
                self.executions,

            "failures":
                self.failures,
        }


class RuntimeIntelligenceController:
    """
    Runtime intelligence execution boundary.

    Responsibilities:

    - lifecycle management
    - capability registration
    - request validation
    - context normalization
    - capability execution
    - stable response formatting
    """

    def __init__(
        self,
        api=None,
    ):
        self.api = (
            api
            if api is not None
            else RuntimeIntelligenceAPI()
        )

        # -----------------------------------------------------
        # Lifecycle state
        # -----------------------------------------------------

        self.initialized = False

        self.running = False

        # -----------------------------------------------------
        # Metrics
        # -----------------------------------------------------

        self.requests = 0

        self.executions = 0

        self.failures = 0

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def start(
        self,
    ) -> bool:
        """
        Initialize and start the controller.
        """

        self.initialized = True

        self.running = True

        return True

    def stop(
        self,
    ) -> bool:
        """
        Stop and de-initialize the controller.

        The gateway tests explicitly expect
        ``initialized`` to become False after stop.
        """

        self.running = False

        self.initialized = False

        return True

    # =========================================================
    # REGISTRATION
    # =========================================================

    def register(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        """
        Register an intelligence capability.
        """

        return self.api.register(
            capability,
            handler,
        )

    # =========================================================
    # CONTEXT NORMALIZATION
    # =========================================================

    def _build_context(
        self,
        request,
    ):
        """
        Normalize supported request forms into
        InvestigationContext.
        """

        if isinstance(
            request,
            InvestigationContext,
        ):
            return request

        if isinstance(
            request,
            str,
        ):
            return InvestigationContext(
                investigation_id=request
            )

        if isinstance(
            request,
            dict,
        ):

            investigation_id = request.get(
                "investigation_id"
            )

            case_id = request.get(
                "case_id"
            )

            capability = request.get(
                "capability"
            )

            payload = request.get(
                "payload",
                request.get(
                    "context"
                ),
            )

            metadata = request.get(
                "metadata",
                {},
            )

            return InvestigationContext(
                investigation_id=investigation_id,

                case_id=case_id,

                capability=capability,

                payload=payload,

                metadata=dict(
                    metadata
                )
                if isinstance(
                    metadata,
                    dict,
                )
                else {},
            )

        return None

    # =========================================================
    # RESPONSE HELPERS
    # =========================================================

    @staticmethod
    def _success(
        result=None,
        context=None,
    ):
        return {
            "success": True,

            "result": result,

            "investigation_id":
                (
                    context.investigation_id
                    if context is not None
                    else None
                ),

            "case_id":
                (
                    context.case_id
                    if context is not None
                    else None
                ),
        }

    @staticmethod
    def _failure(
        message,
        context=None,
    ):
        return {
            "success": False,

            "result": None,

            "error": message,

            "investigation_id":
                (
                    context.investigation_id
                    if context is not None
                    else None
                ),

            "case_id":
                (
                    context.case_id
                    if context is not None
                    else None
                ),
        }

    # =========================================================
    # INVESTIGATION
    # =========================================================

    def investigate(
        self,
        request,
    ):
        """
        Execute an intelligence investigation request.
        """

        self.requests += 1

        context = self._build_context(
            request
        )

        if context is None:

            self.failures += 1

            return self._failure(
                "Invalid intelligence request."
            )

        capability = context.capability

        if not capability:

            self.failures += 1

            return self._failure(
                "Missing capability.",
                context,
            )

        if not context.investigation_id:

            self.failures += 1

            return self._failure(
                "Missing investigation_id.",
                context,
            )

        if not self.api.available(
            capability
        ):

            self.failures += 1

            return self._failure(
                "Capability not registered.",
                context,
            )

        try:

            result = self.api.execute(
                capability,
                context,
            )

            self.executions += 1

            return self._success(
                result=result,
                context=context,
            )

        except Exception as exc:

            self.failures += 1

            return self._failure(
                str(exc),
                context,
            )

    # =========================================================
    # STATUS
    # =========================================================

    def status(
        self,
    ):
        api_status = self.api.status()

        return {
            "healthy": True,

            "initialized":
                self.initialized,

            "running":
                self.running,

            "requests":
                self.requests,

            "executions":
                self.executions,

            "failures":
                self.failures,

            "api":
                api_status,
        }