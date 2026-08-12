from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class InvestigationTrace:
    """
    Enterprise investigation audit trace.

    Stores investigation lifecycle events
    for explainability, auditing, compliance,
    replay, and investigation reconstruction.

    Compatibility:
    - stage
    - type
    - message

    are preserved for existing consumers.
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
        severity: str = "info",
    ) -> None:
        """
        Add an immutable investigation lifecycle event.
        """

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        event = {
            "event_id": str(
                uuid4()
            ),
            "timestamp": timestamp,

            # Backward compatibility fields
            "stage": event_type,
            "type": event_type,
            "message": message,

            # Enterprise audit metadata
            "severity": severity,
            "case_id": self.case_id,

            "details": details or {},
        }

        self.events.append(
            event
        )

    def last_event(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the latest lifecycle event.
        """

        if not self.events:
            return None

        return self.events[-1]

    def count(
        self,
    ) -> int:
        """
        Return total lifecycle events.
        """

        return len(
            self.events
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize trace for API responses,
        storage, and replay.
        """

        return asdict(
            self
        )