"""
Sentinel DNA Runtime Execution Result

Unified execution response object.

Supports:

- Runtime Engine
- Execution Manager
- Runtime Gateway
- Runtime Controller
- Workflow Executor
- Runtime Intelligence layers

Provides both:

Object usage:
    result.success
    result.output

Dictionary compatibility:
    result["success"]
    result["report"]
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """
    Standard runtime execution response.
    """

    success: bool = False

    status: str = "failed"

    message: Optional[str] = None

    error: Optional[str] = None


    # Correlation

    case_id: Optional[str] = None

    investigation_id: Optional[str] = None


    # Runtime objects

    investigation: Any = None

    execution: Any = None

    report: Any = None


    # Payloads

    output: Any = None

    result: Any = None

    data: Any = None


    # Intelligence metadata

    confidence: float = 0.0

    metadata: dict = field(
        default_factory=dict
    )


    # ==================================================
    # Factory Methods
    # ==================================================

    @classmethod
    def ok(
        cls,
        result=None,
        message=None,
        **kwargs,
    ):

        values = dict(kwargs)


        values.setdefault(
            "success",
            True,
        )

        values.setdefault(
            "status",
            "completed",
        )

        values.setdefault(
            "output",
            result,
        )

        values.setdefault(
            "result",
            result,
        )

        values.setdefault(
            "data",
            result,
        )

        values.setdefault(
            "message",
            message,
        )


        return cls(
            **values
        )


    @classmethod
    def success_result(
        cls,
        result=None,
        message=None,
        **kwargs,
    ):

        return cls.ok(
            result=result,
            message=message,
            **kwargs,
        )


    @classmethod
    def failure(
        cls,
        error=None,
        message=None,
        **kwargs,
    ):

        values = dict(kwargs)


        values.setdefault(
            "success",
            False,
        )

        values.setdefault(
            "status",
            "failed",
        )

        values.setdefault(
            "error",
            error,
        )

        values.setdefault(
            "message",
            message,
        )


        return cls(
            **values
        )


    @classmethod
    def fail(
        cls,
        error=None,
        message=None,
        **kwargs,
    ):

        return cls.failure(
            error,
            message,
            **kwargs,
        )


    @classmethod
    def failure_result(
        cls,
        error=None,
        message=None,
        **kwargs,
    ):

        return cls.failure(
            error,
            message,
            **kwargs,
        )


    # ==================================================
    # State
    # ==================================================

    @property
    def failed(
        self,
    ):

        return self.success is False



    def is_success(
        self,
    ):

        return self.success is True



    def is_failed(
        self,
    ):

        return self.failed



    def __bool__(
        self,
    ):

        return self.success is True



    # ==================================================
    # Dictionary Compatibility
    # ==================================================

    def __getitem__(
        self,
        key,
    ):

        values = {

            "success":
                self.success,

            "status":
                self.status,

            "message":
                self.message,

            "error":
                self.error,


            "case_id":
                self.case_id,

            "investigation_id":
                self.investigation_id,


            "investigation":
                self.investigation,

            "execution":
                self.execution,

            "report":
                self.report,


            "output":
                self.output,

            "result":
                self.result,

            "data":
                self.data,


            "confidence":
                self.confidence,


            "metadata":
                self.metadata,


            # compatibility

            "ok":
                self.success,

            "done":
                self.success,

        }


        if key in values:

            return values[key]


        raise KeyError(key)



    def get(
        self,
        key,
        default=None,
    ):

        try:

            return self[key]

        except KeyError:

            return default



    def __contains__(
        self,
        key,
    ):

        try:

            self[key]

            return True

        except KeyError:

            return False



    # ==================================================
    # Metadata
    # ==================================================

    def add_metadata(
        self,
        key,
        value,
    ):

        self.metadata[key] = value

        return self



    def update_metadata(
        self,
        values=None,
        **kwargs,
    ):

        if values:

            self.metadata.update(
                values
            )


        if kwargs:

            self.metadata.update(
                kwargs
            )


        return self



    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ):

        return {

            "success":
                self.success,

            "status":
                self.status,

            "message":
                self.message,

            "error":
                self.error,


            "case_id":
                self.case_id,

            "investigation_id":
                self.investigation_id,


            "investigation":
                self.investigation,

            "execution":
                self.execution,

            "report":
                self.report,


            "output":
                self.output,

            "result":
                self.result,

            "data":
                self.data,


            "confidence":
                self.confidence,


            "metadata":
                dict(
                    self.metadata
                ),

        }