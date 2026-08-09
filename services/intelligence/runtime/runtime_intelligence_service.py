"""
Runtime Intelligence Service

Service layer for runtime intelligence execution.
"""

from typing import Callable, Dict, Any, Optional

from .runtime_intelligence_context import (
    RuntimeIntelligenceContext,
)


class RuntimeIntelligenceService:
    """
    Runtime intelligence capability manager.

    Responsibilities:
    - Register intelligence capabilities
    - Execute capability handlers
    - Track runtime requests
    - Provide runtime status
    """


    def __init__(
        self,
    ):
        self.capabilities = {}

        self.requests = 0



    def register_capability(
        self,
        name: str,
        handler: Callable,
    ):
        """
        Register intelligence capability.
        """

        self.capabilities[name] = handler



    def register(
        self,
        name: str,
        handler: Callable,
    ):
        """
        Alias for compatibility.
        """

        self.register_capability(
            name,
            handler,
        )



    def available(
        self,
        name: Optional[str] = None,
    ):
        """
        Check or list available capabilities.
        """

        if name is not None:

            return name in self.capabilities


        return list(
            self.capabilities.keys()
        )



    def investigate(
        self,
        request,
        context=None,
    ):
        """
        Execute intelligence capability.

        Supports:

        investigate(
            "analysis",
            context
        )

        and:

        investigate(
            {
                "capability": "analysis"
            }
        )
        """

        self.requests += 1


        capability = None

        request_data = {}

        execution_context = context



        if isinstance(
            request,
            str,
        ):

            capability = request



        elif isinstance(
            request,
            dict,
        ):

            capability = request.get(
                "capability"
            )

            request_data = request



        else:

            return None



        if capability not in self.capabilities:

            return None



        if execution_context is None:

            investigation_id = (

                request_data.get(
                    "investigation_id"
                )

                or request_data.get(
                    "case_id"
                )

                or request_data.get(
                    "case"
                )

            )


            execution_context = RuntimeIntelligenceContext(
                investigation_id
            )



        handler = self.capabilities[
            capability
        ]


        result = handler(
            execution_context
        )


        return {
            "success": True,

            "capability":
                capability,

            "case":
                execution_context.investigation_id,

            "investigation_id":
                execution_context.investigation_id,

            "output":
                result,

            "context":
                execution_context,
        }



    def execute(
        self,
        request,
        context=None,
    ):
        """
        Compatibility wrapper.
        """

        return self.investigate(
            request,
            context,
        )



    def clear(
        self,
    ):
        """
        Remove all registered capabilities.
        """

        self.capabilities.clear()



    def status(
        self,
    ):
        """
        Runtime health information.
        """

        return {

            "healthy":
                True,

            "requests":
                self.requests,

            "capabilities":
                list(
                    self.capabilities.keys()
                ),

            "pipeline":
                True,

        }