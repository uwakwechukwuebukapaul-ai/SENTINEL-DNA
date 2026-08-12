"""Central, environment-based runtime configuration for the beta deployment."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class SentinelDNASettings:
    data_dir: str = "data"
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False

    @classmethod
    def from_environment(cls) -> "SentinelDNASettings":
        port = int(os.getenv("SENTINEL_DNA_PORT", "5000"))
        if not 1 <= port <= 65535:
            raise ValueError("SENTINEL_DNA_PORT must be between 1 and 65535")
        return cls(
            data_dir=os.getenv("SENTINEL_DNA_DATA_DIR", "data"),
            host=os.getenv("SENTINEL_DNA_HOST", "127.0.0.1"),
            port=port,
            debug=os.getenv("SENTINEL_DNA_DEBUG", "false").lower() == "true",
        )

    def ensure_data_dir(self) -> Path:
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
