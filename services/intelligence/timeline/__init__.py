"""Investigation timeline services."""

from .timeline_engine import InvestigationTimelineEngine
from .timeline_models import InvestigationTimelineEvent


# Backward compatibility alias
# Older investigation workspace modules use TimelineBuilder.
# The canonical implementation is now InvestigationTimelineEngine.
TimelineBuilder = InvestigationTimelineEngine


__all__ = [
    "InvestigationTimelineEngine",
    "InvestigationTimelineEvent",
    "TimelineBuilder",
]