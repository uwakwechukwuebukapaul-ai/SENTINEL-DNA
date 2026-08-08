"""
Sentinel DNA Execution Tracker

Tracks agent execution lifecycle.

Responsibilities:

- Record executed agents
- Track failures
- Capture execution metrics
- Provide investigation telemetry
"""

from __future__ import annotations

from datetime import datetime, timezone


class ExecutionTracker:
    """
    Investigation execution telemetry.
    """

    def __init__(self) -> None:

        self.started_at = (
            datetime.now(timezone.utc)
        )

        self.completed_agents = []

        self.failed_agents = []

        self.metrics = {
            "total_agents": 0,
            "successful": 0,
            "failed": 0,
        }


    def record_success(
        self,
        agent_name: str,
    ) -> None:

        self.completed_agents.append(
            agent_name
        )

        self.metrics["successful"] += 1
        self.metrics["total_agents"] += 1



    def record_failure(
        self,
        agent_name: str,
    ) -> None:

        self.failed_agents.append(
            agent_name
        )

        self.metrics["failed"] += 1
        self.metrics["total_agents"] += 1



    def summary(
        self,
    ) -> dict:

        return {

            "started_at":
                self.started_at.isoformat(),

            "completed_agents":
                self.completed_agents,

            "failed_agents":
                self.failed_agents,

            "metrics":
                self.metrics,

        }