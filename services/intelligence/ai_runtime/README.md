# AI Runtime Foundation

This package defines the provider boundary for governed AI capabilities. `DeterministicMockProvider` is offline-only, predictable, and intended for tests and synthetic demonstrations. No external AI API calls are made.

The runtime does not execute investigations; `InvestigationCoordinator` and `InvestigationOrchestrator` remain the canonical investigation path.
