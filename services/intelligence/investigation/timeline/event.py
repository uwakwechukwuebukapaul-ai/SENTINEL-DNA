"""
Sentinel DNA Timeline Event
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TimelineEvent:

    name: str

    description: str


    created_at: str = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )