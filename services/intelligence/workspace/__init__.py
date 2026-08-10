"""
Sentinel DNA Analyst Workspace Package.

Provides analyst-ready investigation views.

Components:

- InvestigationView
- EvidenceFormatter
- TimelineBuilder
- AnalystWorkspace
"""

from importlib import import_module


try:
    AnalystWorkspace = import_module(
        f"{__name__}.analyst_workspace"
    ).AnalystWorkspace
except (ImportError, AttributeError):
    AnalystWorkspace = None

from ..timeline import (
    TimelineBuilder,
)


__all__ = [

    "AnalystWorkspace",

    "TimelineBuilder",

]