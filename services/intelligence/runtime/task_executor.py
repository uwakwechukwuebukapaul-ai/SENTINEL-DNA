"""
Sentinel DNA Runtime Task Executor Compatibility Layer

The canonical RuntimeTaskExecutor implementation lives in:

services.intelligence.runtime.runtime_task_executor

This module preserves the legacy import path so existing
runtime integrations do not break.
"""

from __future__ import annotations

from .runtime_task_executor import (
    RuntimeExecutionStatus,
    RuntimeTaskExecutor,
    RuntimeTaskFailure,
)


__all__ = [
    "RuntimeTaskExecutor",
    "RuntimeExecutionStatus",
    "RuntimeTaskFailure",
]
