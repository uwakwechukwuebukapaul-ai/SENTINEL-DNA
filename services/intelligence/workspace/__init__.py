from importlib import import_module

try:
    AnalystWorkspace = import_module(f"{__name__}.analyst_workspace").AnalystWorkspace
except (ImportError, AttributeError):
    AnalystWorkspace = None
from ..timeline import TimelineBuilder
from .aggregation import SOCWorkspaceAggregator
from .models import SOCWorkspaceSnapshot, WorkspaceCaseView, WorkspaceTimelineEntry
from .repository import WorkspaceRepository
from .service import SOCWorkspaceService
__all__ = ["AnalystWorkspace", "TimelineBuilder", "SOCWorkspaceAggregator", "SOCWorkspaceSnapshot", "WorkspaceCaseView", "WorkspaceTimelineEntry", "WorkspaceRepository", "SOCWorkspaceService"]
