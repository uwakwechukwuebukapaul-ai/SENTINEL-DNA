# SIEM normalization

`normalize_event` converts vendor-shaped dictionaries into the deterministic `SecurityEvent` contract. It performs no network calls and preserves the original event under `raw_event`.
