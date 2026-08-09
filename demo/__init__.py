"""
Sentinel DNA Demo Package

Contains executable demonstrations
of AI SOC investigation workflows.
"""

from .demo_runner import run_demo
from .demo_report import DemoReport


__all__ = [
    "run_demo",
    "DemoReport",
]