from __future__ import annotations
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

class ObservabilityService:
    def __init__(self, logger: logging.Logger | None = None): self.logger = logger or logging.getLogger("sentinel_dna")
    def event(self, name: str, **fields: Any) -> None: self.logger.info("%s", {"event": name, **fields})
    def metric(self, name: str, value: Any = 1, **fields: Any) -> None: self.event(name, value=value, **fields)
    @contextmanager
    def measure(self, name: str, **fields: Any) -> Iterator[None]:
        started = time.perf_counter()
        try: yield
        except Exception as exc:
            self.logger.exception("%s", {"event": name, "error": type(exc).__name__, **fields})
            raise
        finally: self.event(name, duration_ms=round((time.perf_counter() - started) * 1000, 2), **fields)
