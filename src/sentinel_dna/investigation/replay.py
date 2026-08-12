"""
Sentinel DNA Investigation Replay Engine.

Provides:
- investigation execution replay records
- lifecycle event storage
- decision reconstruction
- analyst audit visibility
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ReplayEvent:
    """
    Single replayable investigation event.
    """

    stage: str
    message: str
    details: dict[str, Any] = field(
        default_factory=dict
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
    event_id: str = field(
        default_factory=lambda: str(uuid4())
    )


@dataclass
class InvestigationReplay:
    """
    Investigation replay record.

    Stores the complete execution history
    required for investigation reconstruction.
    """

    case_id: str

    replay_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    events: list[ReplayEvent] = field(
        default_factory=list
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def add_event(
        self,
        stage: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Add replay lifecycle event.
        """

        self.events.append(
            ReplayEvent(
                stage=stage,
                message=message,
                details=details or {},
            )
        )

    def timeline(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return chronological replay timeline.
        """

        return [
            asdict(event)
            for event in self.events
        ]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize replay object.
        """

        return {
            "case_id": self.case_id,
            "replay_id": self.replay_id,
            "created_at": self.created_at,
            "events": self.timeline(),
        }