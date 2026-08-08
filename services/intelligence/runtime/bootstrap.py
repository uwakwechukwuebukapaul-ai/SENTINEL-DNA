"""
Sentinel DNA Runtime Bootstrap

Registers built-in investigation capabilities
into the agent registry and runtime executor.
"""

from typing import Any


def analysis_agent(
    payload: dict[str, Any],
):
    """
    Core analysis capability.

    Initial runtime implementation.
    Later replaced by the AI investigation engine.
    """

    alert = payload.get(
        "alert",
        {},
    )

    return {
        "agent": "analysis",
        "status": "completed",
        "finding": {
            "indicator": alert.get(
                "indicator"
            ),
            "severity": alert.get(
                "severity"
            ),
            "source": alert.get(
                "source"
            ),
        },
    }


def bootstrap_agents(
    registry,
    runtime_adapter=None,
):
    """
    Register Sentinel DNA built-in agents.
    """

    registry.register(
        "analysis",
        analysis_agent,
    )


    if runtime_adapter:

        runtime_adapter.register(
            "analysis",
            analysis_agent,
        )