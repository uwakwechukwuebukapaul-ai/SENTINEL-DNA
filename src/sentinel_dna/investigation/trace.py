from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class InvestigationTrace:
    """
    Enterprise investigation audit trace.

    Stores investigation lifecycle events
    for explainability, auditing, replay,
    and compliance.
    """

    case_id: str

    events: list[dict[str, Any]] = field(
        default_factory=list
    )

    def add_event(
        self,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        self.events.append(
            {
                "timestamp": timestamp,
                "stage": event_type,
                "type": event_type,
                "message": message,
                "details": details or {},
            }
        )

    def stages(
        self,
    ) -> list[str]:
        """
        Return executed investigation stages.
        """

        return [
            event["stage"]
            for event in self.events
        ]

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return asdict(
            self
        )